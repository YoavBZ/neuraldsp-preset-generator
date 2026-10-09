"""Bounded independent verification; no project imports or numerical helpers.

Only di from the twelve fixed prepare NPZs is loaded. Save all independent
derivations before parsing any primary result/progress/provenance/input values.
No workers, native assets, model, plugin, network, or Git mutations.
"""
from pathlib import Path
import ast
from collections import Counter
import hashlib
import importlib.metadata
import json
import math
import re
import subprocess
import sys
import time
import traceback

import numpy as np
from scipy.fft import next_fast_len
from scipy.signal import butter, sosfiltfilt

ROOT = Path('/Users/yoavbz/projects/neuraldsp-preset-generator')
RUN = ROOT / 'tmp/di-alignment-control-20261008'
OUT = ROOT / 'tmp/di-alignment-control-verification.json'
MD = ROOT / 'tmp/di-alignment-control-verification.md'
REV = '3ae99769948cf6a09fc7f32ed8f472b4717d5905'
ARMS = ('identity', 'polarity', 'lowpass', 'tanh')
ERRORS = [
    'calibration GCC-PHAT peak sharpness must exceed 10',
    'ambiguous GCC-PHAT peak: separation must exceed 1.2',
    'calibration/catalog lag mismatch', 'calibration half-lag disagreement',
    'calibration filtered correlation below 0.5',
]
OWN = ['learn/di_alignment_control.py', 'tests/test_di_alignment_control.py',
       'docs/di-alignment-control-plan.md', 'docs/di-morgan-flatref-inputs.sha256',
       'docs/di-morgan-control-prepare.json', 'docs/di-morgan-control-verification.json',
       'docs/research/di-morgan-control-independent-2026-10-08.py',
       'docs/research/di-alignment-control-review-2026-10-08.md']
INHERITED = '''docs/di-domain-pilot-inputs.json docs/di-domain-pilot-plan.md
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
TOL = 1e-8
started = time.monotonic()
report = {'status': 'RUNNING', 'revision': REV, 'checks': [], 'failures': [],
          'primary_numerical_values_unread': True, 'derivations': [],
          'main_confirmation': 'User reports session96826 COMPLETE exit0, all156 rows, committed declaration before actual DI access; no other jobs/agents.',
          'float_absolute_tolerance': TOL, 'exact_fields': 'identities, hashes, booleans, integer lags and signs, schema, errors',
          'limitations': [
              '12 reused original takes from one player/guitar; 156 dependent constructed cases are not 156 independent recordings.',
              'Positive catalog priors equal imposed truth: optimistic control, no validation of native priors.',
              'Actual P is not rerun; saved actual-P composition evidence is compared to independent estimates and decisions.',
              'Shares installed NumPy/SciPy FFT/filter implementations, but imports no project numerical code.',
              'Commit-before-access relies on main attestation and frozen guard/source, supported by recorded revision and filesystem timing; no access audit proves first access.',
              'Original preparation QC/oracles and independent verification are inherited evidence, not recomputed here.',
              'No scored interval, threshold tuning, native-study reopening, model/native transfer or product claim.',
              'Primary budget is cooperative; saved timing and file times do not prove interruption of stuck calls.',
          ]}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fh(path):
    with path.open('rb') as f:
        h = hashlib.sha256()
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def ah(x):
    return sha(np.asarray(x, dtype='<f8').tobytes())


def readj(path):
    return json.loads(path.read_text(), parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def check(name, ok, detail=None, required=False):
    row = {'name': name, 'passed': bool(ok)}
    if detail is not None:
        row['detail'] = detail
    report['checks'].append(row)
    if not ok:
        report['failures'].append(row)
        if required:
            raise ValueError(name)
    return bool(ok)


def need(name, ok, detail=None):
    return check(name, ok, detail, True)


def deadline():
    if time.monotonic()-started > 900:
        raise TimeoutError('independent 15-minute cooperative budget exceeded')


def ident(x):
    return {k: x[k] for k in ('slug', 'content', 'take')}


def finite(x):
    if isinstance(x, float):
        return math.isfinite(x)
    if isinstance(x, dict):
        return all(finite(v) for v in x.values())
    if isinstance(x, list):
        return all(finite(v) for v in x)
    return True


def save():
    report['elapsed_seconds'] = time.monotonic()-started
    report['verifier_sha256'] = fh(Path(__file__))
    OUT.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')


def compare_tree(name, own, recorded):
    """Full recursive schema/value comparison; never relative tolerance."""
    discrepancies = []
    leaves = 0
    largest = 0.0
    largest_path = None

    def visit(a, b, path):
        nonlocal leaves, largest, largest_path
        if isinstance(a, dict) and isinstance(b, dict):
            if a.keys() != b.keys():
                discrepancies.append({'path': path, 'own_keys': sorted(a), 'recorded_keys': sorted(b)})
            for k in a.keys() & b.keys():
                visit(a[k], b[k], path+'.'+k)
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                discrepancies.append({'path': path, 'own_length': len(a), 'recorded_length': len(b)})
            for i, (x, y) in enumerate(zip(a, b)):
                visit(x, y, path+f'[{i}]')
        else:
            leaves += 1
            if type(a) is float and type(b) is float and math.isfinite(a) and math.isfinite(b):
                delta = abs(a-b)
                if delta > largest:
                    largest, largest_path = delta, path
                ok = delta <= TOL
            else:
                ok = type(a) is type(b) and a == b
            if not ok:
                discrepancies.append({'path': path, 'independent': a, 'recorded': b})
    visit(own, recorded, name)
    check(name, not discrepancies, {'leaves': leaves, 'max_float_absolute_error': largest,
                                   'max_float_error_path': largest_path, 'discrepancies': discrepancies})


def estimate(reference, observed):
    """Hann GCC with wet*conj(di), linear FFT padding and bounded lag search."""
    size = len(reference)
    fft_size = next_fast_len(2*size-1)
    taper = np.hanning(size)
    spectrum_ref = np.fft.rfft((reference-reference.mean())*taper, fft_size)
    spectrum_obs = np.fft.rfft((observed-observed.mean())*taper, fft_size)
    cross = spectrum_obs * np.conjugate(spectrum_ref)
    amplitude = np.abs(cross)
    hz = np.fft.rfftfreq(fft_size, 1/48000)
    band = (hz >= 80) & (hz <= 4000)
    mask = band & (amplitude > 1e-8*float(np.max(amplitude[band])))
    normalized = np.zeros(cross.shape, dtype=cross.dtype)
    normalized[mask] = cross[mask]/amplitude[mask]
    circular = np.fft.irfft(normalized, fft_size)
    delays = np.arange(-512, 513)
    scores = np.abs(circular[np.remainder(delays, fft_size)])
    winner = int(np.argmax(scores))
    lag = int(delays[winner])
    tiny = np.finfo(float).tiny
    sharp = float(scores[winner]/max(float(np.median(scores)), tiny))
    other = float(np.max(scores[np.abs(delays-lag) > 8]))
    return {'lag': lag, 'sharpness': sharp,
            'peak_separation': float(scores[winner]/max(other, tiny))}


def derive(case, x, y):
    """Full six-second transform; finite prefix shifts; own complete diagnostics."""
    arm, imposed = case['arm'], case['imposed_lag']
    std = float(np.std(y))
    if arm in ('identity', 'mismatch'):
        transformed = y.copy()
    elif arm == 'polarity':
        transformed = -y
    elif arm == 'lowpass':
        transformed = sosfiltfilt(butter(4, 1200, btype='lowpass', fs=48000, output='sos'), y,
                                 padtype='odd', padlen=27)
    elif arm == 'tanh':
        transformed = np.tanh(3*y/std)*std/3
    need(case['case_id']+' full transform finite', transformed.shape == (288000,) and np.isfinite(transformed).all())
    di = np.zeros(481024, np.float64)
    wet = np.zeros_like(di)
    di[:193024] = x[:193024]
    destination = np.arange(193024)
    source = destination-imposed
    available = (source >= 0) & (source < 193024)
    wet[destination[available]] = transformed[source[available]]
    need(case['case_id']+' finite shift and zero tail', not np.any(di[193024:]) and not np.any(wet[193024:])
         and np.array_equal(wet[512:192512], transformed[512-imposed:192512-imposed]))
    recipe = {'origin': 512, 'prefix_samples': 193024, 'total_samples': 481024, 'dtype': '<f8',
              'di_prefix_sha256': ah(di[:193024]), 'wet_prefix_sha256': ah(wet[:193024]),
              'transformed_di6_sha256': ah(transformed), 'tail': 'zeros after prefix_samples'}
    a, b = di[512:192512], wet[512:192512]
    need(case['case_id']+' nonzero calibration', float(np.std(a)) > 0 and float(np.std(b)) > 0)
    estimates = []
    for label, start, stop in [('full', 0, 192000), ('first_half', 0, 96000), ('second_half', 96000, 192000)]:
        estimates.append({'interval': label, **estimate(a[start:stop], b[start:stop])})
    lags = [e['lag'] for e in estimates]
    sharp = [e['sharpness'] for e in estimates]
    sep = [e['peak_separation'] for e in estimates]
    lag = lags[0]
    bp = butter(4, (80, 4000), btype='bandpass', fs=48000, output='sos')
    fa = sosfiltfilt(bp, a, padtype='odd', padlen=27)
    fb = sosfiltfilt(bp, b, padtype='odd', padlen=27)
    if lag > 0:
        fa, fb = fa[:-lag], fb[lag:]
    elif lag < 0:
        fa, fb = fa[-lag:], fb[:lag]
    fa, fb = fa-fa.mean(), fb-fb.mean()
    denominator = float(np.linalg.norm(fa)*np.linalg.norm(fb))
    rho = float(fa @ fb / denominator) if denominator else 0.0
    catalog_error = abs(lag-case['catalog_lag'])
    lag_range = max(lags)-min(lags)
    gates = {'sharpness': [s > 10 for s in sharp], 'peak_separation': [s > 1.2 for s in sep],
             'catalog_within_16': catalog_error <= 16, 'lag_range_within_8': lag_range <= 8,
             'absolute_correlation_at_least_half': math.isfinite(rho) and abs(rho) >= .5}
    decisions = [all(gates['sharpness']), all(gates['peak_separation']), gates['catalog_within_16'],
                 gates['lag_range_within_8'], gates['absolute_correlation_at_least_half']]
    first = next((ERRORS[i] for i, passed in enumerate(decisions) if not passed), None)
    accepted = first is None
    fields = {'lag': lag, 'polarity': 1 if rho >= 0 else -1, 'correlation': rho,
              'sharpness': sharp[0], 'half_lags': lags[1:], 'half_sharpness': sharp[1:],
              'peak_separation': sep[0], 'half_peak_separation': sep[1:]}
    positive = case['positive']
    row = {**case, 'construction': recipe, 'valid': True, 'consistent': True, 'accepted': accepted,
           'estimates': estimates, 'correlation': rho, 'correlation_denominator': denominator,
           'catalog_error': catalog_error, 'lag_range': lag_range, 'gates': gates,
           'derived_fields': fields, 'predicted_first_error': first,
           'actual_fields': fields.copy() if accepted else None,
           'calibrate_first_error': first, 'calibrate_error_type': None if accepted else 'ValueError',
           'estimate_lag_errors': [v-case['truth_lag'] for v in lags] if positive else None,
           'estimated_polarity_correct': fields['polarity'] == case['truth_polarity'] if positive else None,
           'accepted_lag_error': lag-case['truth_lag'] if positive and accepted else None,
           'accepted_polarity_correct': fields['polarity'] == case['truth_polarity'] if positive and accepted else None,
           'nonfinite_diagnostic_fields': []}
    need(case['case_id']+' all diagnostics finite', finite(row))
    return row


def summarize(rows):
    counts = {}
    for arm in (*ARMS, 'mismatch'):
        counts[arm] = {}
        for content in ('all', 'chords', 'scales'):
            part = [r for r in rows if r['arm'] == arm and (content == 'all' or r['content'] == content)]
            accepted = sum(r['accepted'] for r in part)
            counts[arm][content] = {'total': len(part), 'accepted': accepted, 'rejected': len(part)-accepted,
                                    'acceptance_rate': accepted/len(part)}
    wrong = [r for r in rows if r['positive'] and r['accepted'] and
             (abs(r['accepted_lag_error']) > 1 or not r['accepted_polarity_correct'])]
    negatives = [r for r in rows if not r['positive'] and r['accepted']]
    required = {arm: counts[arm]['all']['accepted'] for arm in ('identity', 'polarity')}
    passed = all(v == 36 for v in required.values()) and not wrong and not negatives
    return {'valid': True, 'passed': passed, 'disposition': 'PASS' if passed else 'FAIL',
            'counts_by_arm_content': counts, 'wrong_accepted_positives': wrong,
            'accepted_mismatch_negatives': negatives, 'required_positive_acceptance': required,
            'interpretation': 'Optimistic correct-prior constructed-pair calibration only; no native alignment or model-transfer conclusion.'}


def reasons(rows):
    return {arm: dict(Counter(r['predicted_first_error'] for r in rows if r['arm'] == arm and not r['accepted']))
            for arm in (*ARMS, 'mismatch')}


def main():
    need('actual project helper environment', Path(sys.prefix).resolve() == (ROOT/'.venv').resolve())
    need('bytecode disabled', sys.dont_write_bytecode)
    need('fixed revision', git('rev-parse', 'HEAD').decode().strip() == REV)
    need('fixed branch', git('branch', '--show-current').decode().strip() == 'codex/song-model-continuation')
    report['git_status_before'] = git('status', '--porcelain').decode()
    report['environment'] = {'python': sys.version, 'prefix': sys.prefix,
                             'packages': {k: importlib.metadata.version(k) for k in ('numpy', 'scipy')}}
    need('35 inherited plus eight own distinct pins', len(INHERITED) == 35 and len(set(INHERITED+OWN)) == 43)
    pins = {}
    for name in INHERITED+OWN:
        deadline()
        data = (ROOT/name).read_bytes()
        need('committed dependency '+name, data == git('show', REV+':'+name))
        pins[name] = sha(data)
    report['source_hashes_before'] = pins
    plan = (ROOT/OWN[2]).read_text()
    approval = json.loads(re.search(r'<!-- alignment-approval\n(.*?)\nalignment-approval -->', plan, re.S)[1])
    need('declared reviewed snapshot', '**Declared:' in plan and approval['status'] == 'DECLARED'
         and approval['fresh_independent_review'] is True and approval['mean_interpretation'] == 'uncentered-input-exact-formula')
    for key, name in [('source_sha256', OWN[0]), ('test_sha256', OWN[1]), ('review_sha256', OWN[7])]:
        need('approval '+key, approval[key] == pins[name])
    need('reviewed scientific suffix', sha(plan.split('## Frozen design\n', 1)[1].encode()) == approval['design_sha256'])
    review = (ROOT/OWN[7]).read_text()
    need('review approve and frozen reviewed identities', 'Verdict: APPROVE' in review
         and all(pins[n] in review for n in [OWN[0], OWN[1], *OWN[3:7]]))
    # Reconstruct inherited pin-name declaration without importing any project module.
    r_ast = ast.parse((ROOT/'learn/run_di_domain_pilot.py').read_text())
    r_names = next(ast.literal_eval(n.value) for n in r_ast.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'PINNED' for t in n.targets))
    v_ast = ast.parse((ROOT/'learn/run_di_domain_pilot_v2.py').read_text())
    v_node = next(n.value for n in v_ast.body if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'PINNED' for t in n.targets))
    v_names = [n.value for n in ast.walk(v_node) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    c_ast = ast.parse((ROOT/'learn/di_morgan_control.py').read_text())
    c_names = next(ast.literal_eval(n.value) for n in c_ast.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'OWN_PINS' for t in n.targets))
    need('independent inherited pin identity reconstruction', set(r_names) | set(v_names) | set(c_names) == set(INHERITED))
    correction = readj(ROOT/'docs/di-domain-pilot-v2-inputs.json')
    need('original input declaration frozen', correction['schema'] == 2 and correction['tolerance'] == 1e-8
         and correction['original_inputs'] == 'docs/di-domain-pilot-inputs.json'
         and correction['original_inputs_sha256'] == pins['docs/di-domain-pilot-inputs.json']
         and correction['window_family'] == 'torch32' and correction['window_dtype'] == '<f4')
    manifest = readj(ROOT/'docs/di-domain-pilot-inputs.json')
    takes = manifest['takes']
    need('original 12 unique six per content ordered manifest', len(takes) == 12
         and len({t['slug'] for t in takes}) == len({t['take'] for t in takes}) == 12
         and Counter(t['content'] for t in takes) == {'chords': 6, 'scales': 6}
         and all(re.fullmatch(r'[a-zA-Z0-9_-]+', t['slug']) for t in takes))
    report['takes'] = [ident(t) for t in takes]
    report['attribution'] = manifest['attribution']
    prep = readj(ROOT/OWN[4])
    inherited_verification = readj(ROOT/OWN[5])
    inherited_pins = {k: pins[k] for k in INHERITED}
    need('complete valid original prepare', prep['complete'] is True and prep['valid'] is True
         and [ident(r) for r in prep['rows']] == report['takes'])
    need('successful complete inherited independent verification', inherited_verification['status'] == 'VERIFIED_WITH_EVIDENCE_LIMITS'
         and inherited_verification['failures'] == [] and len(inherited_verification['checks']) > 0
         and all(c['passed'] is True for c in inherited_verification['checks'])
         and inherited_verification['source_pins'] == inherited_pins
         and inherited_verification['verifier_sha256'] == pins[OWN[6]]
         and [ident(r) for r in inherited_verification['preparation']] == report['takes'])
    for stage, rows in [('prepare', prep['rows']), ('inherited independent prepare', inherited_verification['preparation'])]:
        for r in rows:
            oracle = r['oracle_scores']['primary']
            need(stage+' QC/oracle '+r['slug'], r['qc']['valid'] is True
                 and (stage != 'prepare' or r['qc_valid'] is True)
                 and type(oracle) in (int, float) and math.isfinite(oracle) and 0 <= oracle < 1e-6)
    original = ROOT/'tmp/di-morgan-control-20261008/prepare'
    need('original prepare report byte identity', (original/'result.json').read_bytes() == (ROOT/OWN[4]).read_bytes())
    need('original prepare provenance all35 pins', readj(original/'provenance.json')['pins'] == inherited_pins)
    need('inherited verifier archive identity', fh(ROOT/'tmp/di-morgan-control-verification.json') == pins[OWN[5]])
    auxiliary = ['tmp/di-morgan-control-20261008/prepare/result.json',
                 'tmp/di-morgan-control-20261008/prepare/provenance.json', 'tmp/di-morgan-control-verification.json']
    report['prerequisite_hashes_before'] = {n: fh(ROOT/n) for n in auxiliary}
    artifact_names = ['provenance.json', 'inputs.json', 'progress.jsonl', 'result.json']
    primary_files = [RUN/n for n in artifact_names]+[ROOT/'tmp/di-alignment-control-20261008.log']
    need('primary finished evidence files; no failure artifact', all(p.is_file() for p in primary_files) and not (RUN/'failure.json').exists())
    report['primary_artifact_hashes_before'] = {str(p.relative_to(ROOT)): fh(p) for p in primary_files}
    report['primary_stat_before'] = {str(p.relative_to(ROOT)): {'mtime': p.stat().st_mtime, 'size': p.stat().st_size} for p in primary_files}
    # Exactly 36 manifest metadata entries, hashing ONLY its twelve prepare paths.
    expected = {f'tmp/di-morgan-control-20261008/{stage}/{t["slug"]}.npz'
                for stage in ('prepare', 'render', 'infer') for t in takes}
    table = {}
    for line in (ROOT/OWN[3]).read_text().splitlines():
        match = re.fullmatch(r'([a-f0-9]{64})  (.+)', line)
        need('artifact hash manifest line', match is not None)
        h, name = match.groups()
        need('unique declared artifact metadata '+name, name in expected and name not in table)
        table[name] = h
    need('exact36 artifact manifest', set(table) == expected and len(table) == 36)
    selected = {k: v for k, v in table.items() if '/prepare/' in k}
    need('exact12 prepare subset', len(selected) == 12)
    observed = {}
    for name, h in selected.items():
        path = ROOT/name
        need('no aliases/symlinks '+name, path.resolve() == path and not path.is_symlink())
        observed[name] = fh(path)
        need('all12 hash barrier '+name, observed[name] == h)
    report['input_file_hashes_before'] = observed
    loaded = {}
    for t in takes:
        deadline()
        name = f'tmp/di-morgan-control-20261008/prepare/{t["slug"]}.npz'
        need('immediate pre-load hash '+name, fh(ROOT/name) == selected[name])
        with np.load(ROOT/name, allow_pickle=False) as z:
            x = np.asarray(z['di'], dtype=np.float64).copy()
        need('mono finite six-second DI '+t['slug'], x.shape == (288000,) and np.isfinite(x).all() and float(np.std(x)) > 0)
        loaded[t['slug']] = x
    report['di6_sha256'] = {k: ah(v) for k, v in loaded.items()}
    cases = []
    for t in takes:
        for arm in ARMS:
            for lag in (-128, 0, 128):
                cases.append({**ident(t), 'case_id': f'{t["slug"]}:{arm}:{lag}', 'pair': ident(t),
                              'arm': arm, 'positive': True, 'imposed_lag': lag, 'catalog_lag': lag,
                              'truth_lag': lag, 'truth_polarity': -1 if arm == 'polarity' else 1})
    for t in takes:
        group = [q for q in takes if q['content'] == t['content']]
        other = group[(group.index(t)+1) % len(group)]
        cases.append({**ident(t), 'case_id': f'{t["slug"]}:mismatch:0', 'pair': ident(other),
                      'arm': 'mismatch', 'positive': False, 'imposed_lag': 0, 'catalog_lag': 0,
                      'truth_lag': None, 'truth_polarity': None})
    need('exact156 independent declared identities', len(cases) == len({c['case_id'] for c in cases}) == 156)
    report['declared_cases'] = cases
    for i, c in enumerate(cases):
        deadline()
        report['derivations'].append(derive(c, loaded[c['slug']], loaded[c['pair']['slug']]))
        if (i+1) % 12 == 0:
            print(f'Independent derivations {i+1}/156; primary values unread', flush=True)
    report['independent_screen'] = summarize(report['derivations'])
    report['independent_rejection_reasons'] = reasons(report['derivations'])
    wrong = report['independent_screen']['wrong_accepted_positives']
    report['independent_wrong_accepted_summary'] = {
        'case_count': len(wrong),
        'distinct_source_performance_count': len({r['slug'] for r in wrong}),
        'source_performances': sorted({r['slug'] for r in wrong}),
        'by_arm': dict(Counter(r['arm'] for r in wrong)),
        'by_content': dict(Counter(r['content'] for r in wrong)),
        'by_imposed_shift': dict(Counter(str(r['imposed_lag']) for r in wrong)),
        'signed_errors': sorted({r['accepted_lag_error'] for r in wrong}),
        'signed_error_range': [min(r['accepted_lag_error'] for r in wrong), max(r['accepted_lag_error'] for r in wrong)] if wrong else None,
        'absolute_error_range': [min(abs(r['accepted_lag_error']) for r in wrong), max(abs(r['accepted_lag_error']) for r in wrong)] if wrong else None,
        'polarity_error_case_count': sum(not r['accepted_polarity_correct'] for r in wrong),
        'cases': [{k: r[k] for k in ('case_id', 'slug', 'content', 'take', 'arm', 'imposed_lag', 'accepted_lag_error', 'accepted_polarity_correct')} for r in wrong],
        'interpretation': 'Dependent transform/shift effects on reused takes; counts do not estimate an independent-recording failure rate.'}
    report['derived_before_primary_unix'] = time.time()
    report['derivations_sha256_before_primary'] = sha(json.dumps(report['derivations'], sort_keys=True, allow_nan=False).encode())
    report['status'] = 'DERIVED_BEFORE_PRIMARY_COMPARISON'
    save()
    # Mandatory persisted-all156 barrier BEFORE any primary numerical JSON read.
    need('all156 persisted with primary unread', len(readj(OUT)['derivations']) == 156
         and readj(OUT)['primary_numerical_values_unread'] is True)
    report['precomparison_verification_file_sha256'] = fh(OUT)
    report['primary_comparison_started_unix'] = time.time()
    primary = readj(RUN/'result.json')
    progress = [json.loads(line) for line in (RUN/'progress.jsonl').read_text().splitlines()]
    provenance = readj(RUN/'provenance.json')
    inputs = readj(RUN/'inputs.json')
    report['primary_numerical_values_unread'] = False
    check('primary complete exact156 and finite', primary.get('complete') is True and len(primary.get('rows', [])) == 156
          and len(progress) == 156 and finite(primary) and finite(progress))
    compare_tree('all156 result rows including construction estimates Pearson predicates actual and derived fields truth', report['derivations'], primary['rows'])
    check('progress equals result EXACTLY', progress == primary['rows'])
    check('stdout log equals incremental progress bytes', primary_files[-1].read_bytes() == (RUN/'progress.jsonl').read_bytes())
    compare_tree('complete frozen scientific screen', report['independent_screen'], primary['screen'])
    compare_tree('rejection reason counts', report['independent_rejection_reasons'], reasons(primary['rows']))
    compare_tree('exact provenance pins', pins, provenance['pins'])
    compare_tree('exact provenance declared cases', cases, provenance['cases'])
    compare_tree('exact provenance input artifacts', selected, provenance['declared_input_artifacts'])
    compare_tree('exact recorded input file and DI identities', {'artifacts': selected, 'di6_sha256': report['di6_sha256']}, inputs)
    compare_tree('same helper environment Python prefix packages', report['environment'],
                 {k: provenance[k] for k in ('python', 'prefix', 'packages')})
    check('provenance revision and attribution', provenance['git_revision'] == REV
          and primary['attribution'] == provenance['attribution'] == manifest['attribution'])
    commit_time = int(git('show', '-s', '--format=%ct', REV).decode().strip())
    elapsed = primary['elapsed_seconds']
    primary_start = provenance['started_unix']
    report['primary_timing'] = {'commit_unix': commit_time, 'started_unix': primary_start,
                                'elapsed_seconds': elapsed, 'budget_seconds': provenance['budget_seconds']}
    check('commit before primary start; bounded finite timing', type(primary_start) in (int, float)
          and math.isfinite(primary_start) and commit_time <= primary_start
          and type(elapsed) in (int, float) and math.isfinite(elapsed) and 0 <= elapsed <= 900
          and provenance['budget_seconds'] == 900 and primary_start < report['derived_before_primary_unix'])
    check('primary file timing consistent with completion before verification',
          all(primary_start <= p.stat().st_mtime <= report['derived_before_primary_unix'] for p in primary_files)
          and (RUN/'provenance.json').stat().st_mtime <= (RUN/'inputs.json').stat().st_mtime
          <= (RUN/'progress.jsonl').stat().st_mtime <= (RUN/'result.json').stat().st_mtime
          and abs((RUN/'result.json').stat().st_mtime-(primary_start+elapsed)) < 5)
    report['recorded_scientific_disposition'] = primary['screen']['disposition']
    report['source_hashes_after'] = {k: fh(ROOT/k) for k in pins}
    report['prerequisite_hashes_after'] = {n: fh(ROOT/n) for n in auxiliary}
    report['input_file_hashes_after'] = {n: fh(ROOT/n) for n in selected}
    report['primary_artifact_hashes_after'] = {str(p.relative_to(ROOT)): fh(p) for p in primary_files}
    for category in ('source_hashes', 'prerequisite_hashes', 'input_file_hashes', 'primary_artifact_hashes'):
        check(category+' unchanged before/after', report[category+'_before'] == report[category+'_after'])
    check('independent derivations unchanged after comparison', report['derivations_sha256_before_primary']
          == sha(json.dumps(report['derivations'], sort_keys=True, allow_nan=False).encode()))
    check('HEAD remains declaration revision', git('rev-parse', 'HEAD').decode().strip() == REV)
    report['git_status_after'] = git('status', '--porcelain').decode()
    check('Git tracked/worktree state unchanged', report['git_status_before'] == report['git_status_after'])
    report['status'] = 'VERIFY' if not report['failures'] else 'NOTVERIFY'


try:
    main()
except Exception as exc:
    report['status'] = 'NOTVERIFY'
    report['exception'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    print(traceback.format_exc(), flush=True)
finally:
    save()
    lines = ['# Independent declared timing-control verification', '', '**'+report['status']+'**', '',
             'Revision: `'+REV+'`. Independent derivations: '+str(len(report['derivations']))+'/156.', '',
             'Checks: '+str(len(report['checks']))+'; failures: '+str(len(report['failures']))+'.', '',
             'Own NumPy/SciPy constructions, GCC-PHAT, filtering, Pearson, predicates, Calibration fields and gate. '
             'No project numerical functions imported or called. All156 derivations saved before primary numerical comparison.', '']
    if 'independent_screen' in report:
        lines += ['Scientific disposition: **'+report['independent_screen']['disposition']+'**.', '',
                  '| Arm | Accepted | Rejected |', '|---|---:|---:|']
        for arm, content in report['independent_screen']['counts_by_arm_content'].items():
            s = content['all']
            lines.append(f'| {arm} | {s["accepted"]} | {s["rejected"]} |')
        lines += ['', 'Wrong accepted positives: '+str(len(report['independent_screen']['wrong_accepted_positives']))+
                  '; accepted mismatches: '+str(len(report['independent_screen']['accepted_mismatch_negatives']))+'.', '',
                  'Wrong accepted details: `'+json.dumps(report['independent_wrong_accepted_summary'], sort_keys=True)+'`.', '',
                  'Rejection reasons: `'+json.dumps(report['independent_rejection_reasons'], sort_keys=True)+'`.', '']
    if report['failures']:
        lines += ['Failures retained in JSON:', '']+['- '+r['name'] for r in report['failures']]+['']
    if 'exception' in report:
        lines += ['Exception: '+report['exception']['type']+': '+report['exception']['message'], '']
    lines += ['Evidence limits:', '']+['- '+s for s in report['limitations']]+['',
              'Inherited native failure remains closed. Original scientific disposition is retained. Main owns archival, navigation, commits and next steps.', '',
              str(report.get('attribution', 'Pedroza et al., Guitar-TECHS, CC BY 4.0')), '']
    MD.write_text('\n'.join(lines))
    print(json.dumps({'status': report['status'], 'derivations': len(report['derivations']),
                      'checks': len(report['checks']), 'failures': len(report['failures']),
                      'scientific_disposition': report.get('independent_screen', {}).get('disposition')}), flush=True)

sys.exit(0 if report['status'] == 'VERIFY' else 1)
