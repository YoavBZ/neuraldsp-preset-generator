"""Independent attempt-2 result verification; no production imports or subprocesses.

Read definitions as the specification, derive ALL twelve rows in memory before
opening saved native numerical results/NPZs. Never read model or catalog bytes.
Only the two named reports are created, exclusively; bytecode is disabled by CLI.
"""
import ast
import gzip
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback

ROOT = Path('/Users/yoavbz/projects/neuraldsp-preset-generator')
RUN = ROOT / 'tmp/di-domain-pilot-20261008-attempt2'
OUT = ROOT / 'tmp/di-domain-pilot-v2-verification.json'
MD = ROOT / 'tmp/di-domain-pilot-v2-verification.md'
CPU = Path('/Users/yoavbz/ndsp-presets/tools/learn-venv')
assert Path(sys.prefix).resolve() == CPU.resolve()
assert sys.dont_write_bytecode
assert not OUT.exists() and not MD.exists(), 'exclusive reports already exist'
START = time.monotonic()
report = {'schema': 1, 'kind': 'declared result verification, not a new experiment',
          'head_checked_before_execution': 'e49950ba06cd0ae3837d7a1923a7599545387e36',
          'branch_checked_before_execution': 'codex/song-model-continuation',
          'concurrent_navigation_edits_observed': ['docs/README.md', 'docs/ROADMAP.md', 'docs/di-recovery-plan.md', 'learn/README.md'],
          'execution_notes': ['Initial launch stopped during SciPy import: NumPy testing attempted an optional lscpu subprocess; audit denied it before execution. No audio or saved numerical fields were read and no reports created. The original traceback is retained in the tool log. Audit now raises OSError, which that optional import probe handles as unavailable; child execution remains prohibited.'],
          'mismatches': [], 'comparisons': [], 'rows': [], 'read_order': [],
          'access': {'model_bytes_read': False, 'catalog_bytes_read': False,
                     'model_inferences': 0, 'renders': 0, 'children': 0,
                     'audio_reads': [], 'blocked_child_attempts': []}}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def check(label, condition, detail=None):
    if not condition:
        report['mismatches'].append({'check': label, 'detail': detail})
    return bool(condition)


def compare(label, value, saved, tolerance=1e-12):
    if isinstance(value, dict):
        check(label + ': keys', set(value) == set(saved), [list(value), list(saved)])
        for key in value.keys() & saved.keys():
            compare(label + '.' + key, value[key], saved[key], tolerance)
    elif isinstance(value, (list, tuple)):
        check(label + ': length', len(value) == len(saved))
        for i, (a, b) in enumerate(zip(value, saved)):
            compare(label + '[' + str(i) + ']', a, b, tolerance)
    elif isinstance(value, float):
        error = abs(value - saved)
        report['comparisons'].append({'field': label, 'absolute_error': error,
                                      'tolerance': tolerance})
        check(label, math.isfinite(saved) and error <= tolerance,
              {'independent': value, 'saved': saved, 'absolute_error': error})
    else:
        check(label, type(value) is type(saved) and value == saved, [value, saved])


def audit(event, args):
    if event == 'open':
        filename, mode, flags = args
        if isinstance(filename, (str, bytes, os.PathLike)):
            p = Path(os.fsdecode(filename)).resolve()
            if p.suffix == '.pt' or p.name == 'P2-catalog.json':
                raise RuntimeError('forbidden model/catalog read')
            writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (
                isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT))
            if writing and p not in (OUT, MD):
                raise RuntimeError('write outside exclusive report paths: ' + str(p))
    if event in ('subprocess.Popen', 'os.system', 'os.fork', 'os.posix_spawn'):
        report['access']['blocked_child_attempts'].append({'event': event, 'executable': str(args[0]) if args else None})
        raise OSError('child execution forbidden')
    if event.startswith('socket.') and event != 'socket.__new__':
        raise RuntimeError('network forbidden')


sys.addaudithook(audit)
import numpy as np
import scipy
from scipy import signal
from scipy.fft import next_fast_len
import soundfile as sf
import torch

SR, G, C, E, T = 48000, 512, 192000, 288000, 480000
SIZES = (256, 512, 1024, 2048, 4096)
SOS = signal.butter(4, [80, 4000], btype='bandpass', fs=SR, output='sos')
CENTER = slice(72000, 216000)
WINDOWS = {}


def band(x):
    return signal.sosfiltfilt(SOS, x, padtype='odd', padlen=27)


def correlation(di, wet, lag):
    a, b = band(di), band(wet)
    lo, hi = max(0, -lag), min(len(a), len(a) - lag)
    a, b = a[lo:hi], b[lo + lag:hi + lag]
    a, b = a - np.mean(a), b - np.mean(b)
    norm = float(np.sqrt(np.sum(a * a)) * np.sqrt(np.sum(b * b)))
    return float(np.sum(a * b) / norm) if norm else 0.0


def gcc(di, wet):
    # Symmetric Hann (not the periodic metric window), demean before taper.
    length = len(di)
    nfft = next_fast_len(2 * length - 1)
    taper = np.hanning(length)
    d = np.fft.rfft((di - np.mean(di)) * taper, nfft)
    w = np.fft.rfft((wet - np.mean(wet)) * taper, nfft)
    cross = w * np.conjugate(d)
    amp = np.abs(cross)
    freq = np.arange(nfft // 2 + 1) * (SR / nfft)
    inband = (freq >= 80) & (freq <= 4000)
    floor = float(np.max(amp[inband])) * 1e-8
    usable = inband & (amp > floor)
    phat = np.zeros_like(cross)
    phat[usable] = cross[usable] / amp[usable]
    c = np.fft.irfft(phat, nfft)
    lags = np.arange(-G, G + 1)
    peaks = np.abs(c[np.mod(lags, nfft)])
    winner = int(np.argmax(peaks))
    lag = int(lags[winner])
    outside = np.flatnonzero(np.abs(lags - lag) > 8)
    runnerup = int(outside[np.argmax(peaks[outside])])
    peak, median, second = float(peaks[winner]), float(np.median(peaks)), float(peaks[runnerup])
    tiny = np.finfo(np.float64).tiny
    return {'lag': lag, 'sharpness': peak / max(median, tiny),
            'peak_separation': peak / max(second, tiny),
            'peak_absolute': peak, 'median_absolute': median,
            'outside_peak_absolute': second, 'outside_peak_lag': int(lags[runnerup]),
            'fft_length': nfft, 'phat_floor': floor, 'used_bins': int(usable.sum()),
            'correlation': correlation(di, wet, lag)}


def qc(x):
    reasons, metrics = [], {}
    if not np.isfinite(x).all():
        return {'valid': False, 'reasons': ['nonfinite'], 'metrics': {}}
    for name, lo, hi in [('calibration', 0, C), ('score', C, T)]:
        part = x[lo:hi]
        frames = part.reshape(-1, 480)
        levels = np.sqrt(np.mean(frames * frames, axis=1))
        rms = float(np.sqrt(np.mean(part * part)))
        clip = float(np.count_nonzero(np.abs(part) >= .999) / len(part))
        active = float(np.count_nonzero(levels > np.max(levels) * .01) / len(levels))
        metrics[name] = {'rms': rms, 'clipped_fraction': clip, 'active_fraction': active}
        if clip > .0001:
            reasons.append(name + ': clipping')
        if rms < .00001:
            reasons.append(name + ': RMS below 1e-5')
        if active < .8:
            reasons.append(name + ': active fraction below 0.8')
    return {'valid': not reasons, 'reasons': reasons, 'metrics': metrics}


def bounded(take, role, root):
    path = (root / take[role]).resolve()
    assert path.is_relative_to(root) and path.parts[-4] == 'P2_' + take['content']
    assert path.parts[-3] == 'audio'
    assert path.parts[-2] == ('directinput' if role == 'di' else 'micamp')
    start, count = take['start_frame'] - G, T + 2 * G
    assert start >= 0
    with sf.SoundFile(str(path)) as audio:
        assert audio.samplerate == SR and audio.frames >= start + count
        metadata = {'path': str(path), 'seek_frame': start, 'frames_read': count,
                    'samplerate': audio.samplerate, 'channels': audio.channels,
                    'subtype': audio.subtype, 'source_frames_header_only': audio.frames}
        audio.seek(start)
        channels = audio.read(frames=count, dtype='float64', always_2d=True)
    assert channels.shape == (count, metadata['channels']) and np.isfinite(channels).all()
    report['access']['audio_reads'].append(metadata)
    return np.mean(channels, axis=1)


def std(x):
    return .1 * (x / (np.std(x) + 1e-9))


def magnitudes(x, n):
    # Independent layout: frequency x frame; explicit frame indices.
    padded = np.pad(x, (n // 2, n // 2), mode='reflect')
    starts = np.arange(0, len(padded) - n + 1, n // 4)
    frames = padded[starts[:, None] + np.arange(n)[None, :]]
    return np.abs(np.fft.rfft((frames * WINDOWS[n]).T, axis=0)) + 1e-6


def metric(a, b, details=False):
    terms = []
    for n in SIZES:
        A, B = magnitudes(a, n), magnitudes(b, n)
        sc = float(np.sqrt(np.sum((A - B) ** 2)) / (np.sqrt(np.sum(B * B)) + 1e-6))
        log = float(np.mean(np.abs(np.log(A) - np.log(B))))
        terms.append({'fft': n, 'spectral_convergence': sc, 'log_l1': log, 'total': sc + log})
    value = sum(t['total'] for t in terms) / len(terms)
    return (value, terms) if details else value


def torch_reference(a, b):
    # Local definition from the frozen formula, no import of direc or P/R/V.
    aa, bb = torch.tensor(a)[None, :], torch.tensor(b)[None, :]
    terms = []
    with torch.no_grad():
        for n in SIZES:
            win = torch.hann_window(n, device='cpu')
            A = torch.abs(torch.stft(aa, n_fft=n, hop_length=n // 4, win_length=n,
                                    window=win, center=True, pad_mode='reflect',
                                    normalized=False, onesided=True, return_complex=True)) + 1e-6
            B = torch.abs(torch.stft(bb, n_fft=n, hop_length=n // 4, win_length=n,
                                    window=win, center=True, pad_mode='reflect',
                                    normalized=False, onesided=True, return_complex=True)) + 1e-6
            sc = float(torch.linalg.vector_norm(A - B) / (torch.linalg.vector_norm(B) + 1e-6))
            log = float(torch.mean(torch.abs(torch.log(A) - torch.log(B))))
            terms.append({'fft': n, 'spectral_convergence': sc, 'log_l1': log, 'total': sc + log})
    return sum(t['total'] for t in terms) / len(terms), terms


def equalize(x, average):
    # 4096 symmetric-Hann, uncentered, hop1024 power; -40dB active-frame gate.
    offsets = np.arange(0, len(x) - 4096 + 1, 1024)
    frames = x[offsets[:, None] + np.arange(4096)] * np.hanning(4096)
    power = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    energy = power.sum(axis=1)
    db = 10 * np.log10(energy + 1e-20)
    active = db >= 10 * np.log10(energy.max() + 1e-20) - 40
    longterm = power[active].mean(axis=0)
    frequencies = np.fft.rfftfreq(4096, 1 / SR)
    smoothed = np.empty(2049)
    for i, f in enumerate(frequencies):
        selection = (frequencies >= f * 2 ** (-1 / 12)) & (frequencies <= f * 2 ** (1 / 12))
        smoothed[i] = longterm[selection].mean() if selection.any() else longterm[i]
    own = 10 * np.log10(smoothed + 1e-20)
    gain = np.clip(average - (own - own.mean()), -15, 15)
    curve = np.interp(np.fft.rfftfreq(len(x), 1 / SR), frequencies, gain)
    result = np.fft.irfft(np.fft.rfft(x) * np.power(10, curve / 20), n=len(x))
    return result, {'spectrum_sha256': digest(own.astype('<f8').tobytes()),
                    'gain_sha256': digest(gain.astype('<f8').tobytes()),
                    'active_spectrum_frames': int(active.sum()),
                    'total_spectrum_frames': len(active), 'gain_min': float(gain.min()),
                    'gain_max': float(gain.max())}


def fit_and_predict(wet, di):
    x, y = wet[G:C-G], di[G:C-G]
    mx, my = float(np.mean(x)), float(np.mean(y))
    centers = np.arange(128, len(x) - 127, 8)
    design = x[centers[:, None] + np.arange(-128, 128)] - mx
    gram = design.T @ design
    ridge = .001 * np.trace(gram) / 256
    rhs = design.T @ (y[centers] - my)
    taps = np.linalg.solve(gram + ridge * np.identity(256), rhs)
    intercept = my - mx * taps.sum()
    evaluation = wet[C:]
    padded = np.pad(evaluation, (G, G), mode='reflect')
    # Convolution with reversed coefficients implements chronological centered rows.
    prediction = signal.convolve(padded[G-128:G+E+127], taps[::-1], mode='valid', method='direct') + intercept
    assert prediction.shape == (E,) and np.isfinite(prediction).all() and np.isfinite(taps).all()
    diagnostics = {'rows': len(centers), 'ridge': float(ridge), 'input_mean': mx,
                   'target_mean': my, 'intercept': float(intercept),
                   'relative_normal_equation_residual': float(np.linalg.norm((gram + ridge*np.eye(256)) @ taps - rhs) / np.linalg.norm(rhs)),
                   'tap_min': float(taps.min()), 'tap_max': float(taps.max())}
    return taps, float(intercept), prediction, diagnostics


def scores(prediction, target, raw_di):
    p, y = std(prediction[CENTER]), std(target[CENTER])
    return {'primary': metric(p, y), 'canonical_waveform_l1': float(np.mean(np.abs(p - y))),
            'raw_lowband': metric(std(band(prediction)[CENTER]), std(band(raw_di)[CENTER]))}


def main():
    manifest = load(ROOT / 'docs/di-domain-pilot-inputs.json')
    correction = load(ROOT / 'docs/di-domain-pilot-v2-inputs.json')
    report['attribution'] = manifest['attribution']
    report['versions'] = {'python': sys.version, 'prefix': sys.prefix, 'numpy': np.__version__,
                          'scipy': scipy.__version__, 'soundfile': sf.__version__, 'torch': torch.__version__}
    report['verification_tolerances'] = {'scalar_calibration_qc': 1e-12,
        'array_max_absolute': 1e-10, 'score_absolute': 1e-8,
        'note': 'comparison roundoff bounds only; original scientific gates unchanged'}
    # Derive the declared dependency list from source syntax, without importing it.
    rtree = ast.parse((ROOT / 'learn/run_di_domain_pilot.py').read_text())
    base = next(ast.literal_eval(n.value) for n in rtree.body
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PINNED' for t in n.targets))
    vtree = ast.parse((ROOT / 'learn/run_di_domain_pilot_v2.py').read_text())
    expr = next(n.value for n in vtree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'PINNED' for t in n.targets))
    extra = [ast.literal_eval(n) for n in expr.args[0].args[0].elts if not isinstance(n, ast.Starred)]
    names = list(dict.fromkeys(list(base) + extra))
    pins = {name: digest((ROOT / name).read_bytes()) for name in names}
    report['current_pins'] = pins
    provenances = {stage: load(RUN / stage / 'provenance.json') for stage in ('metric', 'numpy', 'native')}
    for stage, provenance in provenances.items():
        compare(stage + ': source pins', pins, provenance['pins'])
        compare(stage + ': attribution', manifest['attribution'], provenance['attribution'])
        want = CPU if stage == 'metric' else ROOT / '.venv'
        compare(stage + ': prefix', str(want), provenance['prefix'])
    check('numpy/native same runtime', provenances['numpy']['packages'] == provenances['native']['packages'])
    report['saved_runtime_provenance'] = provenances
    check('original manifest SHA', pins['docs/di-domain-pilot-inputs.json'] == correction['original_inputs_sha256'])
    check('correction fixed specification', correction['schema'] == 2 and correction['tolerance'] == 1e-8
          and correction['window_family'] == 'torch32' and correction['window_dtype'] == '<f4')
    blob = (ROOT / correction['windows']).read_bytes()
    raw = gzip.decompress(blob)
    check('compressed window hash', digest(blob) == correction['windows_sha256'])
    check('decompressed window hash', digest(raw) == correction['windows_raw_sha256'])
    table = json.loads(raw)
    assert set(table) == set(map(str, SIZES))
    torch.set_num_threads(2)
    assert torch.get_default_dtype() == torch.float32
    report['window_checks'] = []
    for n in SIZES:
        row = table[str(n)]['torch32']
        assert row['dtype'] == '<f4' and len(row['bits']) == n
        assert all(type(v) is int and 0 <= v < 2**32 for v in row['bits'])
        data = np.array(row['bits'], dtype='<u4').tobytes()
        check('window byte hash ' + str(n), digest(data) == row['sha256'])
        window = np.frombuffer(data, dtype='<f4')
        assert np.isfinite(window).all()
        live = torch.hann_window(n, device='cpu').numpy().astype('<f4').tobytes()
        check('live default Torch window bits ' + str(n), live == data)
        WINDOWS[n] = window.astype(np.float64)
        report['window_checks'].append({'fft': n, 'sha256': digest(data), 'live_bit_identical': live == data})
    # Own fixed synthetic signal and references, BEFORE saved numerical reports.
    target = np.random.default_rng(20261008).normal(size=144000) * .1
    synthetic = []
    for i, prediction in enumerate([target.copy(), target * .5, np.roll(target, 52), np.zeros_like(target)]):
        own, terms = metric(prediction, target, True)
        ref, refterms = torch_reference(prediction, target)
        error = abs(own - ref)
        check('independent synthetic parity ' + str(i), error <= 1e-8)
        for term, refterm in zip(terms, refterms):
            for key in ('spectral_convergence', 'log_l1', 'total'):
                check('synthetic component parity ' + str((i, term['fft'], key)), abs(term[key] - refterm[key]) <= 1e-8)
        synthetic.append({'case': i, 'numpy': own, 'torch': ref, 'absolute_error': error,
                          'prediction_sha256': digest(prediction.astype('<f8').tobytes()),
                          'target_sha256': digest(target.astype('<f8').tobytes()),
                          'numpy_components': terms, 'torch_components': refterms})
    report['synthetic_independent'] = synthetic
    check('independent synthetic identity', synthetic[0]['numpy'] < 1e-6)
    report['read_order'].append('independent synthetic references derived before saved metric/NumPy numbers')
    takes = manifest['takes']
    assert len(takes) == len({r['take'] for r in takes}) == len({r['slug'] for r in takes}) == 12
    assert [r['content'] for r in takes] == ['chords'] * 6 + ['scales'] * 6
    root = Path(manifest['source_root']).resolve()
    assert root.name == 'P2-downloads'
    pending_arrays, average = {}, None
    for take in takes:
        slug = take['slug']
        print('independent derivation ' + slug, flush=True)
        dguard, wguard = bounded(take, 'di', root), bounded(take, 'micamp', root)
        dcal, wcal = dguard[G:G+C], wguard[G:G+C]
        estimates = [gcc(dcal, wcal), gcc(dcal[:C//2], wcal[:C//2]), gcc(dcal[C//2:], wcal[C//2:])]
        lags = [v['lag'] for v in estimates]
        lag, corr = lags[0], estimates[0]['correlation']
        polarity = 1 if corr >= 0 else -1
        predicates = [
            ('calibration GCC-PHAT peak sharpness must exceed 10', all(v['sharpness'] > 10 for v in estimates)),
            ('ambiguous GCC-PHAT peak: separation must exceed 1.2', all(v['peak_separation'] > 1.2 for v in estimates)),
            ('calibration/catalog lag mismatch', abs(lag - take['lag_samples']) <= 16),
            ('calibration half-lag disagreement', max(lags) - min(lags) <= 8),
            ('calibration filtered correlation below 0.5', math.isfinite(corr) and abs(corr) >= .5)]
        failures = [reason for reason, passed in predicates if not passed]
        calibration = {'lag': lag, 'polarity': polarity, 'correlation': corr,
                       'sharpness': estimates[0]['sharpness'], 'half_lags': lags[1:],
                       'half_sharpness': [v['sharpness'] for v in estimates[1:]],
                       'peak_separation': estimates[0]['peak_separation'],
                       'half_peak_separation': [v['peak_separation'] for v in estimates[1:]]}
        di, wet = dguard[G:G+T].copy(), polarity * wguard[G+lag:G+lag+T]
        dq, wq = qc(di), qc(wet)
        pairqc = {'valid': dq['valid'] and wq['valid'], 'di': dq, 'wet': wq}
        valid = not failures and pairqc['valid']
        error = failures[0] if failures else ('native pair QC failed' if not pairqc['valid'] else None)
        row = {'slug': slug, 'content': take['content'], 'take': take['take'],
               'catalog_lag': take['lag_samples'], 'estimates_full_firsthalf_secondhalf': estimates,
               'all_calibration_predicates': [{'failure': reason, 'passed': passed} for reason, passed in predicates],
               'calibration': calibration, 'calibration_valid': not failures,
               'qc': pairqc, 'qc_diagnostic_only': bool(failures), 'qc_valid': valid,
               'first_failure': error, 'excerpt_hashes': {'di_float64_mono': digest(dguard.tobytes()),
                                                        'wet_float64_mono': digest(wguard.tobytes())}}
        if valid:
            if average is None:
                avgpath = Path(manifest['average']['path'])
                avgbytes = avgpath.read_bytes()
                assert digest(avgbytes) == manifest['average']['sha256']
                average = np.load(avgpath, allow_pickle=False)
                assert average.shape == (2049,) and np.isfinite(average).all()
                report['average'] = {'path': str(avgpath), 'sha256': digest(avgbytes),
                                     'dtype': str(average.dtype), 'shape': list(average.shape)}
            d, w = di[C:], wet[C:]
            canonical, eqdiag = equalize(d, average)
            flat, flatdiag = equalize(w, average)
            taps, intercept, fir, firdiag = fit_and_predict(wet, di)
            oracle, _ = equalize(d.copy(), average)
            row.update({'target_preprocessing': eqdiag, 'flatref_preprocessing': flatdiag,
                        'fir_fit': firdiag})
            for key, waveform in [('native_input_scores', w), ('flatref_scores', flat),
                                  ('fir_scores', fir), ('oracle_scores', oracle)]:
                row[key] = scores(waveform, canonical, d)
            row['oracle'] = row['oracle_scores']['primary']
            pending_arrays[slug] = {'di': d, 'wet': w, 'target': canonical, 'flatref': flat,
                                    'fir': fir, 'render_di': di[2*SR:],
                                    'fir_taps': taps, 'fir_intercept': np.asarray(intercept)}
            check(slug + ': identity gate', row['oracle'] < 1e-6)
            check(slug + ': baseline denominators', min(row['native_input_scores']['primary'],
                  row['flatref_scores']['primary'], row['native_input_scores']['raw_lowband']) > 0)
        report['rows'].append(row)
    # This marks the hard blind boundary: no saved native row/NPZ numerical
    # fields have been opened by this script, nor by the authoring session.
    report['read_order'].append('ALL 12 estimates, correlations, predicates, fixed alignments, QC and valid-row preprocessing/FIR/scores derived before ANY saved native row/NPZ numerics')
    report['independent_rows_sha256_before_saved_read'] = digest(json.dumps(report['rows'], sort_keys=True, allow_nan=False).encode())
    print('blind derivation complete; now opening saved numerical results', flush=True)
    metric_saved, numpy_saved = load(RUN / 'metric/result.json'), load(RUN / 'numpy/result.json')
    for stage, saved in [('metric', metric_saved), ('numpy', numpy_saved)]:
        check(stage + ': passed', saved.get('passed') is True)
        check(stage + ': exact tolerance', saved.get('tolerance') == 1e-8)
        check(stage + ': cases', [r['case'] for r in saved['rows']] == list(range(4)))
        for own, prior in zip(synthetic, saved['rows']):
            compare(stage + ': score case ' + str(own['case']), own['numpy'], prior['numpy'], 1e-8)
            compare(stage + ': Torch case ' + str(own['case']), own['torch'], prior['torch'], 1e-8)
            compare(stage + ': absolute error case ' + str(own['case']), abs(prior['numpy'] - prior['torch']), prior['absolute_error'], 1e-15)
            check(stage + ': error gate ' + str(own['case']), prior['absolute_error'] <= 1e-8)
            if stage == 'metric':
                for field in ('prediction_sha256', 'target_sha256'):
                    compare(stage + ': signal ' + str(own['case']) + field, own[field], prior[field])
        check(stage + ': identity gate', saved['rows'][0]['numpy'] < 1e-6)
    compare('metric default dtype', 'torch.float32', metric_saved['default_dtype'])
    compare('metric numpy version', provenances['metric']['packages']['numpy'], metric_saved['numpy_version'])
    compare('metric torch version', provenances['metric']['packages']['torch'], metric_saved['torch_version'])
    compare('helper numpy version', provenances['numpy']['packages']['numpy'], numpy_saved['numpy_version'])
    compare('helper references exact metric artifact', digest((RUN / 'metric/result.json').read_bytes()), numpy_saved['metric_result_sha256'])
    for a, b in zip(metric_saved['rows'], numpy_saved['rows']):
        compare('helper saved Torch reference ' + str(a['case']), a['torch'], b['torch'], 0)
    saved_native = load(RUN / 'native/result.json')
    saved_rows = saved_native['rows']
    compare('native declared row order', [r['slug'] for r in takes], [r['slug'] for r in saved_rows])
    actual = {r['slug']: r for r in saved_rows}
    check('native distinct coverage', len(saved_rows) == len(actual) == 12)
    array_reports = []
    for row in report['rows']:
        slug = row['slug']
        saved = actual[slug]
        for field in ('slug', 'content', 'take', 'excerpt_hashes', 'qc_valid'):
            compare(slug + '.' + field, row[field], saved[field])
        if row['calibration_valid']:
            compare(slug + ': calibration', row['calibration'], saved['calibration'])
            compare(slug + ': QC', row['qc'], saved['qc'])
        else:
            check(slug + ': no saved calibration after rejection', 'calibration' not in saved and 'qc' not in saved)
        if row['first_failure']:
            compare(slug + ': first failure', row['first_failure'], saved.get('error'))
            check(slug + ': rejected has no score artifact', not (RUN / 'native' / (slug + '.npz')).exists())
        else:
            check(slug + ': successful no error', 'error' not in saved)
            for key in ('native_input_scores', 'flatref_scores', 'fir_scores', 'oracle_scores', 'oracle'):
                compare(slug + '.' + key, row[key], saved[key], 1e-8)
            with np.load(RUN / 'native' / (slug + '.npz'), allow_pickle=False) as archive:
                expected = pending_arrays[slug]
                check(slug + ': NPZ keys', set(archive.files) == set(expected))
                for key, own in expected.items():
                    prior = archive[key]
                    check(slug + '.' + key + ': shape/dtype/finite', prior.shape == own.shape and prior.dtype == own.dtype and np.isfinite(prior).all())
                    difference = float(np.max(np.abs(own - prior)))
                    exact = own.tobytes() == prior.tobytes()
                    tolerance = 0 if key in ('di', 'wet', 'render_di') else 1e-10
                    check(slug + '.' + key + ': array', difference <= tolerance, difference)
                    array_reports.append({'slug': slug, 'array': key, 'shape': list(prior.shape),
                        'dtype': str(prior.dtype), 'max_absolute_error': difference,
                        'bit_identical': exact, 'tolerance': tolerance,
                        'independent_sha256': digest(own.tobytes()), 'saved_sha256': digest(prior.tobytes())})
    report['array_comparisons'] = array_reports
    valid_rows = [r for r in report['rows'] if r['qc_valid']]
    rejections = {}
    for row in report['rows']:
        if row['first_failure']:
            rejections[row['first_failure']] = rejections.get(row['first_failure'], 0) + 1
    report['counts'] = {'declared': 12, 'independently_derived': len(report['rows']),
        'bounded_source_reads': len(report['access']['audio_reads']),
        'gcc_estimates': sum(len(r['estimates_full_firsthalf_secondhalf']) for r in report['rows']),
        'calibration_pass': sum(r['calibration_valid'] for r in report['rows']),
        'valid': len(valid_rows), 'rejected': 12 - len(valid_rows),
        'valid_chords': sum(r['content'] == 'chords' for r in valid_rows),
        'valid_scales': sum(r['content'] == 'scales' for r in valid_rows),
        'first_failure_counts': rejections, 'npz_arrays_checked': len(array_reports),
        'scalar_scores_checked': len(valid_rows) * 13, 'renders': 0, 'inferences': 0}
    compare('native complete flag', True, saved_native.get('complete'))
    compare('native valid flag', len(valid_rows) == 12, saved_native.get('valid'))
    compare('native attribution', manifest['attribution'], saved_native['attribution'])
    compare('native NPZ coverage', sorted(pending_arrays), sorted(p.stem for p in (RUN / 'native').glob('*.npz')))
    check('no render or infer directories', not (RUN / 'render').exists() and not (RUN / 'infer').exists())
    check('no render/infer logs', not (ROOT / 'tmp/di-domain-pilot-attempt2-render.log').exists()
          and not (ROOT / 'tmp/di-domain-pilot-attempt2-infer.log').exists())
    progress_bytes = (RUN / 'native/progress.jsonl').read_bytes()
    progress_rows = [json.loads(line) for line in progress_bytes.splitlines()]
    check('progress exactly matches final rows', progress_rows == saved_rows)
    check('native log exactly matches progress', (ROOT / 'tmp/di-domain-pilot-attempt2-native.log').read_bytes() == progress_bytes)
    assets = load(RUN / 'native/assets.json')
    for key, value in assets.items():
        if key in pins:
            compare('native asset source ' + key, pins[key], value)
    report['saved_assets'] = assets
    report['model_identity_limit'] = 'Declared model SHA is recorded from manifest; checkpoint bytes deliberately not read. Native asset record pins source/catalog/revision, not model/average byte hashes. Average independently rehashed; catalog selection taken from authoritative manifest.'
    report['declared_model_identity'] = manifest['model']
    compare('saved native revision', report['head_checked_before_execution'], assets['git_revision'])
    preserved = sorted(p for p in RUN.rglob('*') if p.is_file())
    preserved += [ROOT / ('tmp/di-domain-pilot-attempt2-' + stage + '.log') for stage in ('metric', 'numpy', 'native')]
    report['preserved_artifact_sha256'] = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in preserved}
    report['decision'] = {'native_complete': True, 'native_valid': len(valid_rows) == 12,
        'all12_coverage_control_pass': len(valid_rows) == 12,
        'render_infer_authorized_by_gates': False, 'disposition': 'INCONCLUSIVE',
        'native_neural_screen': 'not evaluated', 'morgan_control': 'not evaluated',
        'fir_all12_control': 'not evaluated: incomplete valid coverage',
        'interpretation': 'Declared calibration/QC rejected the required complete twelve-take pairing. This does not measure neural transfer, prove recording-domain failure, establish irrecoverability, support selection of replacement takes, or authorize tuning/training. Valid-subset scores are diagnostic only.'}


try:
    main()
    report['completed'] = True
except Exception as exc:
    report['completed'] = False
    report['failure'] = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    print(report['failure']['traceback'], flush=True)
report['elapsed_seconds'] = time.monotonic() - START
report['verifier_sha256'] = digest(Path(__file__).read_bytes())
report['verified'] = report['completed'] and not report['mismatches']
report['verdict'] = 'VERIFIED QC STOP; SCIENTIFIC SCREEN INCONCLUSIVE' if report['verified'] else 'VERIFICATION FAILED; NO SCIENTIFIC DECISION'
with OUT.open('x') as f:
    json.dump(report, f, indent=2, allow_nan=False)
    f.write('\n')
lines = ['# Attempt-2 independent result verification', '', '**' + report['verdict'] + '**', '',
         report.get('attribution', 'Pedroza et al., Guitar-TECHS, CC BY 4.0, https://zenodo.org/records/14963133'), '',
         'Verifier imports only standard/numerical libraries, never production P/R/V or direc functions. All twelve independent native derivations precede saved row/NPZ numerical reads. No model checkpoint/catalog read, rendering, inference, new experiment, alternative alignment, threshold, timing, crop, or selection.', '',
         '## Exact counts', '', '```json', json.dumps(report.get('counts', {}), indent=2), '```', '',
         '## Independent calibration diagnostics', '',
         'Full / first half / second half; correlations are signed. QC after a failed calibration is diagnostic only and never rescues rejection.', '',
         '| Take | Lags | Sharpness | Peak separation | Full correlation | First failure |',
         '|---|---|---|---|---|---|']
for row in report['rows']:
    es = row['estimates_full_firsthalf_secondhalf']
    lines.append('| ' + row['slug'] + ' | ' + '/'.join(str(e['lag']) for e in es) + ' | ' +
                 '/'.join(format(e['sharpness'], '.9g') for e in es) + ' | ' +
                 '/'.join(format(e['peak_separation'], '.9g') for e in es) + ' | ' +
                 format(es[0]['correlation'], '.12g') + ' | ' + (row['first_failure'] or 'valid') + ' |')
lines += ['', '## Verification evidence', '',
          '- The JSON records all 36 estimates, PHAT floors/used bins/peaks/runner-up lags, all calibration predicates and full/half correlations, 48 interval QC reports, 24 source-slice hashes and exact bounded-read definitions.',
          '- Compressed/decompressed coefficient hashes and all 7,936 Torch32 coefficient bytes checked; live CPU Torch default float32 Hann bits checked without changing its default dtype. Independent synthetic component/aggregate references use only the four declared signals. Both saved runtime reports, source pins, versions, signal hashes, reference linkage and absolute 1e-8 gates checked.',
          '- Valid-row DI/wet/render preparation requires exact bytes. Canonical target/flatref independently reconstruct the original spectrum/smoothing/mean removal/clamp/FFT formula using the pinned average. Calibration-only centered 256-tap ridge/intercept and reflected evaluation prediction independently recomputed. Array comparison tolerance is 1e-10 absolute; scalar score tolerance is 1e-8; calibration/QC 1e-12. These are verification roundoff bounds and do not alter scientific gates.',
          '- All valid-row primary, waveform L1 and raw-DI low-band baseline/flatref/FIR/oracle scores checked. JSON retains every array and scalar absolute error; native complete/valid and exact coverage checked, progress compared with final rows and log. No render/infer artifacts or logs exist.',
          '', 'Mismatches: **' + str(len(report['mismatches'])) + '**.', '',
          '```json', json.dumps(report['mismatches'], indent=2), '```', '',
          '## Interpretation and limits', '', report.get('decision', {}).get('interpretation', 'Verification did not complete.'), '',
          report.get('model_identity_limit', ''), '',
          'Historical absence of execution is supported by complete run inventory, native-only logs/progress and stage guards, not by an independent operating-system execution audit. Rejected rows lacked saved estimate diagnostics because production stops at the first calibration exception; the independent report fills these in without changing rejection.', '',
          'HEAD/branch and unchanged frozen source dependencies were checked outside this script using read-only git commands. Concurrent navigation edits were observed in docs/README.md, docs/ROADMAP.md, docs/di-recovery-plan.md and learn/README.md and left untouched. JSON preserves source pins, run/log artifact hashes, verifier hash, versions, access inventory and derivation order. Existing run and failed logs were preserved; only this script and the two exclusive reports were written. No result documentation or git mutation performed.']
if 'failure' in report:
    lines += ['', '## Retained verification failure', '', '```', report['failure']['traceback'], '```']
with MD.open('x') as f:
    f.write('\n'.join(lines) + '\n')
print(json.dumps({'verdict': report['verdict'], 'counts': report.get('counts'),
                  'mismatches': report['mismatches'], 'elapsed_seconds': report['elapsed_seconds']}), flush=True)
