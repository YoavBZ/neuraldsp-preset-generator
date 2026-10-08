"""Independent, synthetic-only verifier; execute with the existing CPU Torch Python.

No production probe or pilot metric imports, subprocesses, interpreter changes,
audio, datasets, model assets, saved arrays, downloads, or Git mutations.
All numerical predictions are completed before opening any saved case/result.
Only the inert, hash-checked direc.mrstft is used as a frozen external reference.
"""
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path('/Users/yoavbz/projects/neuraldsp-preset-generator')
ART = ROOT / 'tmp/di-domain-metric-probe-20261008-v1'
OUT = ROOT / 'tmp/di-domain-metric-probe-verification.json'
FFTS = (256, 512, 1024, 2048, 4096)
TOL = 1e-8
RAW_TOL = 1e-12
COMMIT = '6dee3047c6994e73b7ebf519f3fa66cd749c95f5'
# Independently obtained with git show COMMIT:path | shasum -a 256 before execution.
PINS = {
    'learn/di_domain_metric_probe.py': '7e56ac6c856cea35e0e1b3f7370605879880c7a0369d1be6f8d044683cbc0f6f',
    'tests/test_di_domain_metric_probe.py': '2df0f788d88408ec6b4e60e688e74bbea6768332e579bee2882f88eabe3b7cff',
    'docs/di-domain-metric-probe-plan.md': '0a3effae2c583e778ca59c6904307797cf045433de57fe3b8a405f2bbdccd563',
    'docs/di-domain-pilot-metric.json': '02f53d2521fe268c28b05ff4b00b806d8199028f5c5ed3764970fff5327513b7',
    'learn/direc.py': '43b698ba69fc97d91b547e9948b9b0611dec7b01453eef43609e365a85885969',
    'learn/di_domain_pilot.py': 'af4358ee3717d9b828a1875262489047a896e953531cc2ca814750344d570eb3',
    'learn/__init__.py': '950da993349f85949c8094f0787bcf1b56f149cf3a7a829f8b7986bea7c3525d',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def forbid_children_network(event, args):
    if event.startswith(('subprocess.', 'socket.')) or event in (
            'os.system', 'os.fork', 'os.forkpty', 'os.posix_spawn',
            'os.exec', 'os.spawn'):
        raise RuntimeError('Forbidden child process or network event: ' + event)


sys.addaudithook(forbid_children_network)
if not sys.dont_write_bytecode:
    raise RuntimeError('Launch with PYTHONDONTWRITEBYTECODE=1 / -B')
if Path(sys.executable).parent != Path('/Users/yoavbz/ndsp-presets/tools/learn-venv/bin'):
    raise RuntimeError('Use the explicit existing CPU Torch interpreter')
if OUT.exists():
    raise RuntimeError('Refusing to overwrite an existing verification')

started = time.monotonic()
declaration = (ROOT / 'docs/di-domain-metric-probe-plan.md').read_text()
if '**Declared: 2026-10-08, before execution.**' not in declaration:
    raise RuntimeError('Unexpected declaration')
current_pins = {name: digest((ROOT / name).read_bytes()) for name in PINS}
if current_pins != PINS:
    raise RuntimeError('Frozen source hash mismatch')
provenance = json.loads((ART / 'provenance.json').read_text())
if provenance['pins'] != PINS:
    raise RuntimeError('Run source hash mismatch')

import numpy as np
import torch

sys.path.insert(0, str(ROOT))
from learn.direc import mrstft as frozen_mrstft

torch.set_num_threads(2)
assert torch.get_default_dtype() == torch.float32
environment = {
    'python': sys.version, 'torch': torch.__version__,
    'torch_build': torch.version.git_version, 'numpy': np.__version__,
    'threads': torch.get_num_threads(), 'device': 'cpu',
    'default_dtype': str(torch.get_default_dtype()), 'input_dtype': 'float64',
}
env_checks = {k: environment[k] == v for k, v in provenance['versions'].items()}

# Decode every coefficient through canonical unsigned LITTLE-ENDIAN IEEE bits.
# There are 7,936 coefficients per table and three precision/construction tables.
saved_windows = json.loads((ART / 'windows.json').read_text())
assert set(saved_windows) == {str(n) for n in FFTS}
decoded = {kind: {} for kind in ('np64', 'torch32', 'torch64')}
window_checks = []
window_predictions = {}
for n in FFTS:
    own_np = .5 - .5 * np.cos(2 * np.pi * np.arange(n) / n)
    own_t32 = torch.hann_window(n, periodic=True, dtype=torch.float32, device='cpu')
    own_t64 = torch.hann_window(n, periodic=True, dtype=torch.float64, device='cpu')
    default = torch.hann_window(n, device='cpu')
    checks = {'fft': n, 'default_matches_explicit32': torch.equal(default, own_t32),
              'default_dtype_float32': default.dtype == torch.float32}
    own = {'np64': own_np, 'torch32': own_t32.numpy(), 'torch64': own_t64.numpy()}
    prediction = {}
    for kind, dtype, uint in (('np64', '<f8', '<u8'), ('torch32', '<f4', '<u4'),
                              ('torch64', '<f8', '<u8')):
        entry = saved_windows[str(n)][kind]
        limit = 2 ** (32 if uint == '<u4' else 64)
        valid_bits = all(type(v) is int and 0 <= v < limit for v in entry['bits'])
        assert valid_bits
        bits = np.asarray(entry['bits'], dtype=np.dtype(uint))
        data = bits.tobytes(order='C')
        values = np.frombuffer(data, dtype=np.dtype(dtype)).copy()
        own_bytes = np.asarray(own[kind], dtype=np.dtype(dtype)).tobytes(order='C')
        checks[kind] = {
            'length': len(values), 'length_valid': values.shape == (n,),
            'dtype_valid': entry['dtype'] == dtype, 'unsigned_bits_valid': valid_bits,
            'canonical_hash_valid': digest(data) == entry['sha256'],
            'construction_byte_identical': data == own_bytes,
            'finite': bool(np.isfinite(values).all()),
        }
        prediction[kind] = {'dtype': dtype, 'bits': np.frombuffer(own_bytes, dtype=uint).tolist(),
                            'sha256': digest(own_bytes)}
        decoded[kind][n] = values
    prediction.update({
        'default_equals_explicit32': bool(torch.equal(default, own_t32)),
        'default_hann_dtype': str(default.dtype),
        'numpy_cast32_equals_torch32': bool(np.array_equal(own_np.astype(np.float32), own_t32.numpy())),
        'max_np64_vs_torch32': float(np.max(np.abs(own_np - own_t32.numpy()))),
        'max_np64_vs_torch64': float(np.max(np.abs(own_np - own_t64.numpy()))),
    })
    window_predictions[str(n)] = prediction
    window_checks.append(checks)


def np_components(prediction, target, windows):
    """Own STFT via explicit reflected samples and indexed frame gathering.

    Frames are (time, frequency), unlike Torch's (batch, frequency, time).
    No production function, sliding-window view, or saved numeric metric is used.
    """
    components = []
    aggregate = 0.0
    for n in FFTS:
        frame_starts = np.arange(0, len(target) + 1, n // 4)
        sample_indices = frame_starts[:, None] + np.arange(n)[None, :]
        window = np.asarray(windows[n], dtype=np.float64)

        def spectrum(signal):
            padded = np.pad(signal, (n // 2, n // 2), mode='reflect')
            return np.abs(np.fft.rfft(padded[sample_indices] * window, n=n, axis=1)) + 1e-6

        p, y = spectrum(prediction), spectrum(target)
        delta = p - y
        # Independent explicit sum of squares, rather than production linalg.norm.
        sc = float(np.sqrt(np.sum(delta * delta)) / (np.sqrt(np.sum(y * y)) + 1e-6))
        ll = float(np.sum(np.abs(np.log(p) - np.log(y))) / p.size)
        components.append({'fft': n, 'spectral_convergence': sc, 'log_l1': ll, 'total': sc + ll})
        aggregate += sc + ll
    return {'aggregate': aggregate / len(FFTS), 'terms': components}


def torch_components(prediction, target, windows):
    """Own explicit-window reference, with every STFT convention specified."""
    p = torch.from_numpy(prediction).reshape(1, -1)
    y = torch.from_numpy(target).reshape(1, -1)
    terms = []
    running = 0.0
    for n in FFTS:
        def spectrum(signal):
            return torch.abs(torch.stft(
                signal, n_fft=n, hop_length=n // 4, win_length=n,
                window=windows[n], center=True, pad_mode='reflect',
                normalized=False, onesided=True, return_complex=True)) + 1e-6
        a, b = spectrum(p), spectrum(y)
        sc = torch.norm(a - b) / (torch.norm(b) + 1e-6)
        ll = torch.mean(torch.abs(torch.log(a) - torch.log(b)))
        # Frozen function's sequential addition is part of exact reference gate.
        running = running + sc + ll
        terms.append({'fft': n, 'spectral_convergence': float(sc), 'log_l1': float(ll),
                      'total': float(sc + ll)})
    return {'aggregate': float(running / len(FFTS)), 'terms': terms}


def component_errors(left, right):
    errors = {'aggregate': abs(left['aggregate'] - right['aggregate'])}
    assert len(left['terms']) == len(right['terms']) == len(FFTS)
    for n, a, b in zip(FFTS, left['terms'], right['terms']):
        assert a['fft'] == b['fft'] == n
        for key in ('spectral_convergence', 'log_l1', 'total'):
            assert math.isfinite(a[key]) and math.isfinite(b[key])
            errors[str(n) + '/' + key] = abs(a[key] - b[key])
    assert math.isfinite(left['aggregate']) and math.isfinite(right['aggregate'])
    return errors


def agrees(left, right):
    return max(component_errors(left, right).values()) <= TOL


target = np.random.default_rng(20261008).normal(size=144000) * 0.1
predictions = (target.copy(), target * 0.5, np.roll(target, 52), np.zeros_like(target))
input_manifest = {
    'seed': 20261008, 'length': 144000, 'scale': 0.1, 'roll': 52,
    'dtype': str(target.dtype), 'target_sha256': digest(target.astype('<f8').tobytes()),
    'case_prediction_sha256': [digest(p.astype('<f8').tobytes()) for p in predictions],
    'generation': 'np.random.default_rng(20261008).normal(size=144000) * 0.1',
    'saved_signal_hashes_available': False,
}
tw32 = {n: torch.from_numpy(decoded['torch32'][n]) for n in FFTS}
tw64 = {n: torch.from_numpy(decoded['torch64'][n]) for n in FFTS}
tnp64 = {n: torch.from_numpy(decoded['np64'][n]) for n in FFTS}
independent_rows = []
extra_rows = []
with torch.no_grad():
    for index, prediction in enumerate(predictions):
        assert time.monotonic() - started < 900
        numpy64 = np_components(prediction, target, decoded['np64'])
        shared32 = np_components(prediction, target, decoded['torch32'])
        torch32 = torch_components(prediction, target, tw32)
        shared64 = torch_components(prediction, target, tnp64)
        torch64 = torch_components(prediction, target, tw64)
        frozen = float(frozen_mrstft(torch.from_numpy(prediction)[None], torch.from_numpy(target)[None]))
        frozen_per_fft = [float(frozen_mrstft(torch.from_numpy(prediction)[None],
                                            torch.from_numpy(target)[None], ffts=(n,))) for n in FFTS]
        dtype = str(torch.stft(torch.from_numpy(prediction), 256, 64,
                              window=tw32[256], return_complex=True).dtype)
        independent_rows.append({
            'index': index, 'original_numpy': numpy64['aggregate'], 'original_torch': frozen,
            'numpy_t32': shared32, 'torch_t32': torch32, 'numpy_np64': numpy64,
            'torch_np64': shared64, 'torch_t64': torch64,
            'torch64_diagnostic_agreement': agrees(numpy64, torch64),
            'stft_output_dtype': dtype,
        })
        discrepancy = frozen - numpy64['aggregate']
        intervention = shared32['aggregate'] - numpy64['aggregate']
        extra_rows.append({
            'index': index, 'original_absolute_error': abs(discrepancy),
            'signed_original_discrepancy': discrepancy, 'signed_window_intervention': intervention,
            'signed_explanation_residual': intervention - discrepancy,
            'shared_t32_errors': component_errors(shared32, torch32),
            'shared_np64_errors': component_errors(numpy64, shared64),
            'torch64_diagnostic_errors': component_errors(numpy64, torch64),
            'frozen_per_fft': frozen_per_fft,
            'explicit_t32_per_fft_equals_frozen': [a['total'] == b for a, b in zip(torch32['terms'], frozen_per_fft)],
        })
        print(json.dumps({'independent_case_derived': index,
                          'saved_case_result_metrics_opened': False}), flush=True)

# First opening of saved case/result metrics: independent numerical work is done.
derivation_finished_before_saved_metrics = True
original_bytes = (ROOT / 'docs/di-domain-pilot-metric.json').read_bytes()
original_run_bytes = (ROOT / 'tmp/di-domain-pilot-20261008/metric/result.json').read_bytes()
original = json.loads(original_bytes)
saved_result = json.loads((ART / 'result.json').read_text())
saved_cases = [json.loads((ART / ('case-%d.json' % i)).read_text()) for i in range(4)]
assert len(original['rows']) == len(saved_result['rows']) == len(saved_cases) == 4
assert sorted(p.name for p in ART.glob('case-*.json')) == ['case-%d.json' % i for i in range(4)]
for row, old in zip(independent_rows, original['rows']):
    delta = row['original_torch'] - row['original_numpy']
    shift = row['numpy_t32']['aggregate'] - row['original_numpy']
    row['checks'] = {
        'reproduced': abs(row['original_numpy'] - old['numpy']) <= 1e-12
                      and abs(row['original_torch'] - old['torch']) <= 1e-12,
        'same_original_pass_pattern': (abs(delta) <= TOL) == (old['absolute_error'] <= TOL),
        'explicit_t32_equals_frozen_exactly': row['torch_t32']['aggregate'] == row['original_torch'],
        'explicit_np64_matches_original': abs(row['numpy_np64']['aggregate'] - row['original_numpy']) <= 1e-12,
        'shared_t32_components_agree': agrees(row['numpy_t32'], row['torch_t32']),
        'shared_np64_components_agree': agrees(row['numpy_np64'], row['torch_np64']),
        'signed_intervention_accounts_for_error': abs(shift - delta) <= TOL,
    }

comparison = {'float_count': 0, 'bool_count': 0, 'integer_count': 0, 'string_count': 0,
              'max_absolute_float_error': 0.0, 'max_error_path': None, 'mismatches': []}


def compare(expected, observed, path):
    if isinstance(expected, dict):
        if not isinstance(observed, dict) or set(expected) != set(observed):
            comparison['mismatches'].append({'path': path, 'reason': 'dictionary keys differ'})
            return
        for key in expected:
            compare(expected[key], observed[key], path + '/' + key)
    elif isinstance(expected, list):
        if not isinstance(observed, list) or len(expected) != len(observed):
            comparison['mismatches'].append({'path': path, 'reason': 'list lengths differ'})
            return
        for i, (a, b) in enumerate(zip(expected, observed)):
            compare(a, b, path + '/' + str(i))
    elif type(expected) is float:
        comparison['float_count'] += 1
        error = abs(expected - observed) if type(observed) in (float, int) else math.inf
        if error > comparison['max_absolute_float_error']:
            comparison['max_absolute_float_error'] = error
            comparison['max_error_path'] = path
        if not math.isfinite(error) or error > RAW_TOL:
            comparison['mismatches'].append({'path': path, 'expected': expected, 'observed': observed})
    else:
        kind = {bool: 'bool_count', int: 'integer_count', str: 'string_count'}[type(expected)]
        comparison[kind] += 1
        if type(expected) is not type(observed) or expected != observed:
            comparison['mismatches'].append({'path': path, 'expected': expected, 'observed': observed})


compare(window_predictions, saved_windows, 'windows')
for index, row in enumerate(independent_rows):
    compare(row, saved_cases[index], 'case-' + str(index))
    compare(row, saved_result['rows'][index], 'result/rows/' + str(index))
independent_pass = all(window_predictions[str(n)]['default_equals_explicit32'] for n in FFTS)
independent_pass = independent_pass and all(all(r['checks'].values()) for r in independent_rows)
compare(independent_pass, saved_result['passed'], 'result/passed')

log_lines = [json.loads(line) for line in (ROOT / 'tmp/di-domain-metric-probe-20261008-v1.log').read_text().splitlines() if line]
expected_log = [{'case': r['index'], 'checks': r['checks']} for r in independent_rows]
compare(expected_log, log_lines, 'log')
assert set(saved_result) == {'passed', 'rows', 'elapsed_seconds'}
elapsed = saved_result['elapsed_seconds']
commit_epoch = 1791457081.0  # 2026-10-08 10:58:01 UTC, git commit inspected before run.
artifact_times = {p.name: p.stat().st_mtime for p in ART.iterdir() if p.is_file()}

def all_window_checks():
    for entry in window_checks:
        if not entry['default_matches_explicit32'] or not entry['default_dtype_float32']:
            return False
        for kind in decoded:
            if not all(v for k, v in entry[kind].items() if k != 'length'):
                return False
    return True


gates = {
    'all_seven_current_and_run_pins_equal_declared_commit': current_pins == PINS == provenance['pins'],
    'original_failure_byte_identical_to_original_run': original_bytes == original_run_bytes,
    'recorded_environment_exactly_reproduced': all(env_checks.values()),
    'all_window_lengths_dtypes_bits_hashes_and_constructions_valid': all_window_checks(),
    'all_raw_metrics_checks_metadata_and_saved_copies_match': not comparison['mismatches'],
    'four_cases_five_ffts': len(independent_rows) == 4 and sum(FFTS) == 7936,
    'all_28_required_case_gates': all(all(r['checks'].values()) for r in independent_rows),
    'all_20_explicit_t32_fft_totals_exactly_equal_frozen': all(all(r['explicit_t32_per_fft_equals_frozen']) for r in extra_rows),
    'overall_probe_pass_independently_reproduced': independent_pass == saved_result['passed'] is True,
    'default_dtype_unchanged': torch.get_default_dtype() == torch.float32,
    'bytecode_disabled': sys.dont_write_bytecode,
    'production_metrics_opened_only_after_derivation': derivation_finished_before_saved_metrics,
    'run_elapsed_finite_within_15_minute_budget': type(elapsed) in (float, int) and math.isfinite(elapsed) and 0 <= elapsed <= 900,
    'all_artifact_mtimes_after_declaration_commit': all(t > commit_epoch for t in artifact_times.values()),
    'no_failure_artifact': not (ART / 'failure.json').exists(),
}
for name in independent_rows[0]['checks']:
    gates['all_cases/' + name] = all(r['checks'][name] for r in independent_rows)

def largest(key):
    return max(max(r[key].values()) for r in extra_rows)

max_errors = {
    'all_recomputed_saved_float_fields': comparison['max_absolute_float_error'],
    'shared_t32_any_component_or_aggregate': largest('shared_t32_errors'),
    'shared_np64_any_component_or_aggregate': largest('shared_np64_errors'),
    'torch64_diagnostic_any_component_or_aggregate': largest('torch64_diagnostic_errors'),
    'shared_t32_aggregate': max(r['shared_t32_errors']['aggregate'] for r in extra_rows),
    'shared_np64_aggregate': max(r['shared_np64_errors']['aggregate'] for r in extra_rows),
    'signed_explanation_residual': max(abs(r['signed_explanation_residual']) for r in extra_rows),
    'original_numpy_torch': max(r['original_absolute_error'] for r in extra_rows),
    'original_artifact_reproduction': max(abs(r[k] - o[old]) for r, o in zip(independent_rows, original['rows'])
                                           for k, old in [('original_numpy', 'numpy'), ('original_torch', 'torch')]),
    'np64_vs_torch32_coefficient': max(r['max_np64_vs_torch32'] for r in window_predictions.values()),
    'np64_vs_torch64_coefficient': max(r['max_np64_vs_torch64'] for r in window_predictions.values()),
}
passed = all(gates.values())
report = {
    'passed': passed, 'declared_commit': COMMIT, 'tolerance': TOL, 'raw_comparison_tolerance': RAW_TOL,
    'gates': gates, 'counts': {
        'cases': 4, 'ffts': 5, 'coefficients_per_table': sum(FFTS),
        'coefficient_tables': 15, 'total_coefficient_entries': 3 * sum(FFTS),
        'required_case_gates': 28, 'exact_frozen_fft_checks': 20,
        'raw_metric_float_fields_per_case': 82, 'raw_metric_float_fields': 328,
        'component_comparisons_per_shared_window_intervention': 64,
    },
    'max_errors': max_errors, 'artifact_comparison': comparison,
    'window_checks': window_checks, 'window_metadata': {
        n: {k: v for k, v in row.items() if k not in decoded} for n, row in window_predictions.items()
    },
    'environment': environment, 'environment_checks': env_checks,
    'additional_environment': {'executable': sys.executable, 'uname': list(os.uname()),
        'torch_config': torch.__config__.show(), 'no_grad_during_numeric_work': True,
        'stft_output_dtype': independent_rows[0]['stft_output_dtype'],
        'numpy_stft_dtype': str(np.fft.rfft(target[:256]).dtype)},
    'source_pins': current_pins, 'input_manifest': input_manifest,
    'independent_rows': independent_rows, 'comparisons_by_case': extra_rows,
    'original_failure_sha256': digest(original_bytes),
    'original_run_result_sha256': digest(original_run_bytes),
    'artifact_sha256': {p.name: digest(p.read_bytes()) for p in ART.iterdir() if p.is_file()},
    'artifact_mtimes_epoch': artifact_times, 'declaration_commit_epoch': commit_epoch,
    'verifier_sha256': digest(Path(__file__).read_bytes()),
    'independent_elapsed_seconds': time.monotonic() - started,
    'interpretation': {
        'window_cause_supported_at_declared_resolution': passed,
        'safe_to_propose_separately_declared_window_table_correction_retaining_1e_minus_8': passed,
        'correction': 'Preserve frozen actual Torch float32 coefficient tables and promote them losslessly for NumPy scoring; a final cast of NumPy Hann is insufficient.',
        'scope': 'Four declared float64 synthetic pairs, five FFT sizes, this recorded CPU/runtime environment.',
        'neural_training_tested': False, 'neural_transfer_tested': False,
        'audio_or_model_or_ranking_tested': False, 'long_training_authorized': False,
        'bitwise_fft_identity_established': False,
        'limitations': [
            'No saved input-signal hashes exist; input identity is reconstructed from the declaration and pinned generator source, not independently attested historical arrays.',
            'Artifact mtimes and declaration commit support ordering; mtimes are not tamper-proof run timestamps.',
            'Explicit NumPy baseline is independently derived from the pinned source definition and checked against saved original metrics; the production NumPy function is never imported or executed.',
            'Recorded environment lacks CPU model and full build configuration; these are recorded for this verification but cannot be retrospectively compared.',
        ],
    },
}
with OUT.open('x') as output:
    json.dump(report, output, indent=2, allow_nan=False)
    output.write('\n')
print(json.dumps({'passed': passed, 'counts': report['counts'], 'max_errors': max_errors,
                  'gates': gates, 'output': str(OUT)}), flush=True)
if not passed:
    raise SystemExit(1)
