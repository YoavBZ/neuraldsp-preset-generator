"""Rank margin and the degradation ladder (`docs/rank-margin-ladder-plan.md`). Development only.

    .venv/bin/python -m learn.rank_margin step-a                  # zero renders
    $TORCH_PY -m learn.rank_margin rebuild                        # C′ 1-h and fold-2 extras (CPU)
    .venv/bin/python -m learn.rank_margin build-variants          # numpy; the ladder and proxies
    .venv/bin/python -m learn.rank_margin render --shard 0/4      # step B, Morgan, isolate=True
    .venv/bin/python -m learn.rank_margin report                  # D1–D3, fragility, per part

m_w(v) = log d_w(S; v) − log d_w(T; v): the judge against the cell's fake recording, settings
rendered through DI variant v, over window w. Outputs go to ~/ndsp-presets/learn/rank-margin/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import random
import shutil
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

SR = 48000
LATENCY = 52                       # Morgan's render latency
SEED = 20261017                    # every draw in step B
BOOT_SEED, BOOT_DRAWS = 20261018, 10_000
CAP = 1200                         # hard stop on step-B renders (plan, budget)
MIN_FREE_GB = 31.0
RENDERS_PER_VARIANT = 3            # warm-up S, S, T
CREST_TOL = 0.2                    # dB
ENV_FLOOR_DB = 3.0                 # proxy 2: the measure DI's own log-envelope std
INFORMATIVE_GAP = 0.1              # amendment 2: d_S − d_T on half B through the measure DI
WINDOWS = {"A": (1.0, 5.5), "B": (5.5, 10.0), "full": (1.0, 10.0)}
MASKS = ("v", "measure")
LAG_TOL = 3                        # samples
BANDS = ((80, 200), (200, 1000), (2000, 8000))
_ACTIVITY = ("pauses", "plays in too few frames")

# --- the declared variants (plan, step B) -------------------------------------------------------

CREST = {"crest-1.5": 1.5, "crest-3": 3.0, "crest-5": 5.0}
SHELF = {"shelf-2": -2.0, "shelf-4": -4.0}
BELL = {"bell+1": 1.0, "bell+3": 3.0, "bell+5": 5.0}
SMEAR = {"env-smear-10": 10.0, "env-smear-30": 30.0}
BLEED = {"bleed-20": -20.0, "bleed-10": -10.0}
MEASURE_ROWS = ("base", *CREST, "placebo-smear", *SMEAR, *SHELF, *BELL, "phase-scramble", *BLEED,
                "cprime-env-swap", "cprime-spectrum", "cprime-crest")
REAL_ROWS = ("cprime", "cprime-1h", "cprime-oracle-eq", "transplant-5", "transplant-10",
             "cprime-eq-transplant-10")
EXTRAS = ("cprime-s1", "cprime-s2", "C", "R", "L")          # fold-2 cells only, descriptive
REPEAT_ROWS = ("base", "cprime", "cprime-oracle-eq")        # rendered first; checked
PURE_EQ = ("placebo-smear", *SHELF, *BELL, "cprime-spectrum")  # coherence is exactly 1
REAL_ONLY = (*REAL_ROWS, *EXTRAS)
TRANSPLANTS = ("transplant-5", "transplant-10", "cprime-eq-transplant-10")
PROXIES = ("crest_err", "env_corr", "spread_err", "onset_err", "band_200_1k", "band_2k_8k",
           "coherence", "lsd")
BASELINES = ("coherence", "lsd")


def home():
    return pathlib.Path("~/ndsp-presets").expanduser()


def out_dir():
    return home() / "learn/rank-margin"


def control_dir():
    return home() / "learn/song-settings/armA-control"


DIAG3 = PLUGIN_ROOT / "docs/audits/song-settings-control-2026-10-15/diag3.json"


def cell_key(slug, amp):
    return f"{slug}|{amp}"


def _tag(slug, amp):
    return f"{slug}-{amp}"


# --- signal helpers -----------------------------------------------------------------------------

def rms(x):
    import numpy as np

    return float(np.sqrt(np.mean(np.asarray(x, np.float64) ** 2)) + 1e-12)


def envelope(x, w_ms):
    """Centred moving RMS over w ms (zero-phase)."""
    import numpy as np

    n = max(1, int(round(w_ms * SR / 1000)))
    return np.sqrt(np.maximum(np.convolve(np.asarray(x, np.float64) ** 2, np.ones(n) / n, mode="same"), 0))


def crest_db(x):
    """20·log10 of the 99.9th-percentile |x| over the RMS (`diag4.py`)."""
    import numpy as np

    return float(20 * np.log10(np.percentile(np.abs(x), 99.9) / rms(x)))


def lt(x):
    """Mean-removed long-term spectrum (`di_robustness.smoothed_spectrum`), on SPEC_N bins."""
    from learn.di_robustness import smoothed_spectrum

    s = smoothed_spectrum(x)
    return s - s.mean()


def band_levels(x, ref):
    """Mean dB difference (mean-removed long-term spectra) of x against ref, per BANDS."""
    import numpy as np

    f = np.fft.rfftfreq(4096, 1 / SR)
    d = lt(x) - lt(ref)
    return [float(d[(f >= a) & (f < b)].mean()) for a, b in BANDS]


def to_lufs(x):
    from learn.direc_check import to_lufs as _t

    return _t(x)


def eq_to(x, gain_db):
    from learn.direc_check import eq_to as _e

    return _e(x, gain_db)


def match_spectrum(x, source, passes=2):
    """x equalised (zero-phase) to `source`'s mean-removed long-term spectrum."""
    y = x
    target = lt(source)
    for _ in range(passes):
        y = eq_to(y, target - lt(y))
    return y


def _ratio(num_env, den_env, num_rms, den_rms):
    """num/den envelope ratio, each floored 60 dB below its signal's RMS, clipped to ±30 dB."""
    import numpy as np

    a = np.maximum(num_env, num_rms * 1e-3)
    b = np.maximum(den_env, den_rms * 1e-3)
    return np.clip(a / b, 10 ** (-30 / 20), 10 ** (30 / 20))


def finish_dyn(y, source):
    """Dynamics rungs end here: re-EQ to the source's long-term spectrum, then −22.9 LUFS."""
    return to_lufs(match_spectrum(y, source))


def compress(x, theta_db, ratio, w_ms=10.0):
    """Static compressor on the w-ms centred RMS envelope: g = −(1 − 1/R)·max(0, e − θ) dB."""
    import numpy as np

    e = 20 * np.log10(envelope(x, w_ms) + 1e-12)
    g = -(1 - 1 / ratio) * np.maximum(0.0, e - theta_db)
    return x * 10 ** (g / 20)


def compress_to_crest(x, delta_db, ratios=(4.0, 10.0), iters=40):
    """(y, meta): x compressed and re-EQ'd so its final crest is crest(x) − delta_db ± 0.2 dB.
    θ is bisected on [e_max − 60, e_max] on the final (re-EQ'd, LUFS-matched) signal. If no
    ratio reaches the target, y is R = 10's lowest-θ output and meta['reached'] is False."""
    import numpy as np

    c0 = crest_db(x)
    if delta_db <= 0:
        return np.array(x, copy=True), {"reached": True, "ratio": None, "theta": None,
                                        "crest_change": 0.0}
    target = c0 - delta_db
    emax = float(20 * np.log10(envelope(x, 10.0).max() + 1e-12))

    def final(theta, r):
        y = finish_dyn(compress(x, theta, r), x)
        return y, crest_db(y)

    y_strong = None
    for r in ratios:
        lo, hi = emax - 60.0, emax
        y_strong, c_strong = final(lo, r)
        if c_strong > target + CREST_TOL:
            continue                                         # unreachable at this ratio
        best = (abs(c_strong - target), y_strong, lo, c_strong)
        for _ in range(iters):
            mid = (lo + hi) / 2
            y, c = final(mid, r)
            if abs(c - target) < best[0]:
                best = (abs(c - target), y, mid, c)
            if abs(c - target) <= CREST_TOL / 4:
                break
            if c > target:
                hi = mid                                     # more compression needed
            else:
                lo = mid
        if best[0] <= CREST_TOL:
            return best[1], {"reached": True, "ratio": r, "theta": best[2], "crest_change": best[3] - c0}
    c = crest_db(y_strong)
    return y_strong, {"reached": False, "ratio": ratios[-1], "theta": emax - 60.0, "crest_change": c - c0}


def placebo_smear(x):
    """`di_robustness`'s "mild" smear: the audio convolved with a normalised 10-ms exponential,
    50/50 dry (about a 16-Hz low-pass on half the signal). The declared placebo."""
    import numpy as np

    t = np.arange(int(0.05 * SR)) / SR
    h = np.exp(-t / 0.010)
    h /= h.sum()
    return to_lufs(0.5 * x + 0.5 * np.convolve(x, h)[:len(x)])


def envelope_smear(x, tau_ms):
    """x · s_τ(e₁)/e₁: e₁ the 1-ms RMS envelope, s_τ a causal one-pole on it; re-EQ, LUFS."""
    from scipy.signal import lfilter

    e1 = envelope(x, 1.0)
    a = math.exp(-1.0 / (tau_ms * SR / 1000))
    s = lfilter([1 - a], [1, -a], e1)
    r = rms(x)
    return finish_dyn(x * _ratio(s, e1, r, r), x)


def shelf_curve(gain_db):
    import numpy as np

    f = np.maximum(np.fft.rfftfreq(4096, 1 / SR), 1.0)
    return gain_db / (1 + (2000 / f) ** 4)


def bell_curve(gain_db, lo=200.0, hi=1000.0, skirt_oct=0.5):
    import numpy as np

    f = np.maximum(np.fft.rfftfreq(4096, 1 / SR), 1.0)
    lf = np.log2(f)
    g = np.zeros_like(f)
    g[(f >= lo) & (f <= hi)] = 1.0
    left = (lf >= np.log2(lo) - skirt_oct) & (f < lo)
    g[left] = 0.5 * (1 - np.cos(np.pi * (lf[left] - (np.log2(lo) - skirt_oct)) / skirt_oct))
    right = (f > hi) & (lf <= np.log2(hi) + skirt_oct)
    g[right] = 0.5 * (1 + np.cos(np.pi * (lf[right] - np.log2(hi)) / skirt_oct))
    return gain_db * g


def shelf(x, gain_db):
    return to_lufs(eq_to(x, shelf_curve(gain_db)))


def bell(x, gain_db):
    return to_lufs(eq_to(x, bell_curve(gain_db)))


def phase_scramble(x, seed, ref):
    """Phases of STFT bins ≥ 1 kHz (1024 Hann, hop 256) made uniform random; re-EQ to `ref`."""
    import numpy as np
    from scipy.signal import istft, stft

    f, _, Z = stft(x, fs=SR, window="hann", nperseg=1024, noverlap=768)
    rng = np.random.default_rng(seed)
    hi = f >= 1000
    Z[hi] = np.abs(Z[hi]) * np.exp(1j * rng.uniform(0, 2 * np.pi, Z[hi].shape))
    _, y = istft(Z, fs=SR, window="hann", nperseg=1024, noverlap=768)
    y = np.pad(y, (0, max(0, len(x) - len(y))))[:len(x)]
    return to_lufs(match_spectrum(y, ref))


def bleed(x, other, db):
    import numpy as np

    y = np.array(x, np.float64, copy=True)
    n = min(len(other), len(y))
    y[:n] += other[:n] / rms(other[:n]) * rms(x) * 10 ** (db / 20)
    return to_lufs(y)


def envelope_swap(x, donor, w_ms=10.0):
    """x carrying donor's w-ms envelope; re-EQ to x, LUFS (row 16)."""
    return finish_dyn(x * _ratio(envelope(donor, w_ms), envelope(x, w_ms), rms(donor), rms(x)), x)


def spectrum_swap(x, donor):
    """x equalised by (donor's mean-removed spectrum − x's), LUFS (row 17)."""
    return to_lufs(eq_to(x, lt(donor) - lt(x)))


def oracle_eq(reb, measure):
    """`diag3.py`'s `rebEQ`, exactly: one pass, then LUFS (row 21)."""
    return to_lufs(eq_to(reb, lt(measure) - lt(reb)))


def transplant(x, ref, w_ms, eq_to_ref=False):
    """x with ref's w-ms envelope; re-EQ back to x's spectrum (rows 22–23), or to ref's (row 24)."""
    y = x * _ratio(envelope(ref, w_ms), envelope(x, w_ms), rms(ref), rms(x))
    return finish_dyn(y, ref if eq_to_ref else x)


def gcc_lag(x, ref, below_hz=None, maxlag=2000):
    """Samples x lags ref (GCC-PHAT, as `diag1.py`), band-limited below `below_hz` if given."""
    import numpy as np

    n = 1 << int(np.ceil(np.log2(len(x) + len(ref))))
    X = np.fft.rfft(x, n) * np.conj(np.fft.rfft(ref, n))
    X /= np.abs(X) + 1e-12
    if below_hz is not None:
        X[np.fft.rfftfreq(n, 1 / SR) >= below_hz] = 0
    c = np.fft.irfft(X, n)
    c = np.concatenate([c[-maxlag:], c[:maxlag + 1]])
    return int(np.argmax(np.abs(c)) - maxlag)


# --- proxies (D3) -------------------------------------------------------------------------------

def _frames_db(x, n=480):
    import numpy as np

    k = len(x) // n
    return 10 * np.log10((np.asarray(x[:k * n]) ** 2).reshape(k, n).mean(1) + 1e-20)


def env_floor_ok(measure_w):
    """The measure DI's own log-envelope std (480-sample frames within 40 dB of its loudest)."""
    e = _frames_db(measure_w)
    return float(e[e >= e.max() - 40].std()) >= ENV_FLOOR_DB


def _spread(x):
    """P90–P10 frame RMS (dB) over playing frames, as `sound_desc.describe` (2048, hop 512)."""
    import numpy as np

    n = 1 + (len(x) - 2048) // 512
    idx = np.arange(2048)[None, :] + 512 * np.arange(n)[:, None]
    r = 10 * np.log10(np.mean(np.asarray(x)[idx] ** 2, axis=1) + 1e-20)
    p = r >= r.max() - 40
    return float(np.percentile(r[p], 90) - np.percentile(r[p], 10))


def _flux(x):
    import numpy as np
    from scipy.signal import stft

    _, _, Z = stft(x, fs=SR, window="hann", nperseg=1024, noverlap=768)
    L = np.log(np.abs(Z) + 1e-9)
    return np.maximum(np.diff(L, axis=1), 0).sum(0)


def _coherence_1_3k(a, b):
    """1–3 kHz magnitude-squared coherence, `nperseg` 4096 (`residual_eval._coherence`'s band)."""
    import numpy as np
    from scipy.signal import coherence

    f, c = coherence(a, b, fs=SR, nperseg=4096)
    return float(np.mean(c[(f >= 1000) & (f < 3000)]))


def _lsd(a, b):
    import numpy as np
    from scipy.signal import stft

    f, _, A = stft(a, fs=SR, window="hann", nperseg=2048, noverlap=1536)
    _, _, B = stft(b, fs=SR, window="hann", nperseg=2048, noverlap=1536)
    m = (f >= 80) & (f <= 10000)
    d = 20 * np.log10(np.abs(A[m]) + 1e-9) - 20 * np.log10(np.abs(B[m]) + 1e-9)
    return float(np.mean(np.sqrt(np.mean(d ** 2, axis=0))))


def proxies(v, measure, window):
    """The 8 proxies of v against the measure DI over `window`, signed so higher is better.
    env_corr is None where the measure DI fails the envelope floor in that window."""
    import numpy as np

    a, b = (int(t * SR) for t in WINDOWS[window])
    vw, mw = np.asarray(v[a:b], np.float64), np.asarray(measure[a:b], np.float64)
    ev, em = _frames_db(vw), _frames_db(mw)
    k = min(len(ev), len(em))
    ev, em = ev[:k], em[:k]
    play = em >= em.max() - 40
    fv, fm = _flux(vw), _flux(mw)
    bl = band_levels(vw, mw)
    return {
        "crest_err": -abs(crest_db(vw) - crest_db(mw)),
        "env_corr": float(np.corrcoef(ev[play], em[play])[0, 1]) if env_floor_ok(mw) else None,
        "spread_err": -abs(_spread(vw) - _spread(mw)),
        "onset_err": -(1 - float(np.corrcoef(fv, fm)[0, 1])),
        "band_200_1k": -abs(bl[1]),
        "band_2k_8k": -abs(bl[2]),
        "coherence": _coherence_1_3k(vw, mw),
        "lsd": -_lsd(vw, mw),
    }


# --- cells, data, draws -------------------------------------------------------------------------

def cells():
    from learn import song_settings as SS

    return SS.control_cells()


def draw_bleed(parts, control_bands, seed=SEED):
    """The bleed part: `random.Random(seed)` picks a band among `parts`' bands outside
    `control_bands` (Honey excluded), then a part in it."""
    ps = {s: p for s, p in parts.items() if s != "telefunken-Honey-GTR"}
    bands = sorted({p["band"] for p in ps.values()} - set(control_bands))
    rng = random.Random(seed)
    b = rng.choice(bands)
    return rng.choice(sorted(s for s, p in ps.items() if p["band"] == b))


def bleed_part():
    from learn import knob_ceiling as K

    ps = K.parts()
    return draw_bleed(ps, {ps[s]["band"] for s, _ in cells()})


def load_results(d=None):
    d = d or control_dir()
    return {cell_key(s, a): json.loads((d / f"{_tag(s, a)}-result.json").read_text()) for s, a in cells()}


def informative_from(results):
    """Amendment 2's rule on the stored results: d_S − d_T ≥ 0.1 on half B (measure DI)."""
    return sorted(k for k, r in results.items() if r["S"]["B"] - r["target"]["B"] >= INFORMATIVE_GAP)


def informative():
    return informative_from(load_results())


# --- the margin ---------------------------------------------------------------------------------

def distance(fake, y, mask, lag, window):
    """(distance or None, used_fallback, reason): the judge with the activity fallback."""
    from analysis.aligned import aligned_distance

    a, b = WINDOWS[window]
    kw = dict(lag=lag, render_latency=LATENCY, start_s=a, end_s=b)
    d = aligned_distance(fake, y, mask, **kw)
    if d.distance is None and any(s in (d.reason or "") for s in _ACTIVITY):
        d2 = aligned_distance(fake, y, fake, **kw)
        return d2.distance, True, d2.reason
    return d.distance, False, d.reason


def margin(d_s, d_t):
    if d_s is None or d_t is None or not (d_s > 0 and d_t > 0) or math.isinf(d_s) or math.isinf(d_t):
        return None
    return math.log(d_s) - math.log(d_t)


# --- step A -------------------------------------------------------------------------------------

def _ceil(frac, n):
    return math.ceil(frac * n - 1e-9)


def step_a_rule(rows):
    """rows: [{'run': 'measure'|'cprime', 'm': float, 'success': bool}] on informative searches.
    Provisional if agreement ≥ 15/18 (rescaled) and, in the C′ run, m > 0 on ≥ 2/3 of its
    successes and m ≤ 0 on ≥ 2/3 of its failures; screen only at 13–14/18 or when the C′ row
    fails; not adopted at ≤ 12/18."""
    n = len(rows)
    agree = sum((r["m"] > 0) == r["success"] for r in rows)
    cp = [r for r in rows if r["run"] == "cprime"]
    succ, fail = [r for r in cp if r["success"]], [r for r in cp if not r["success"]]
    hit_s, hit_f = sum(r["m"] > 0 for r in succ), sum(r["m"] <= 0 for r in fail)
    c_row = hit_s >= _ceil(2 / 3, len(succ)) and hit_f >= _ceil(2 / 3, len(fail))
    table = {"m>0&ok": sum(r["m"] > 0 and r["success"] for r in rows),
             "m>0&miss": sum(r["m"] > 0 and not r["success"] for r in rows),
             "m<=0&ok": sum(r["m"] <= 0 and r["success"] for r in rows),
             "m<=0&miss": sum(r["m"] <= 0 and not r["success"] for r in rows)}
    if agree >= _ceil(15 / 18, n) and c_row:
        verdict = "provisional"
    elif agree >= _ceil(13 / 18, n):
        verdict = "screen"
    else:
        verdict = "not adopted"
    return {"n": n, "agree": agree, "table": table, "cprime_successes_hit": [hit_s, len(succ)],
            "cprime_failures_hit": [hit_f, len(fail)], "cprime_row": c_row, "verdict": verdict}


def combine_lags(by_lag):
    """The two lags must agree; otherwise the reading is undecided (screen only)."""
    vs = {v["verdict"] for v in by_lag.values()}
    return vs.pop() if len(vs) == 1 else "screen (lags disagree)"


def step_a_rows(results, diag3, keys, lag, half="A"):
    rows = []
    for k in keys:
        r = results[k]
        rows.append({"cell": k, "run": "measure", "m": margin(r["S"][half], r["target"][half]),
                     "success": r["measure_run"]["gap_closed_B"] >= 0.5,
                     "gap": r["measure_run"]["gap_closed_B"]})
        d = diag3[k]
        rows.append({"cell": k, "run": "cprime", "m": margin(d[f"reb/S/lag{lag}"][half], d[f"reb/T/lag{lag}"][half]),
                     "success": r["rebuilt_run"]["gap_closed_B"] >= 0.5,
                     "gap": r["rebuilt_run"]["gap_closed_B"]})
    return rows


def step_a():
    """Zero renders: the stored control results and diag3.json."""
    from scipy.stats import spearmanr

    results = load_results()
    diag3 = json.loads(DIAG3.read_text())
    fb = {k: r.get("fallback", 0) for k, r in results.items()}
    if any(fb.values()):
        raise SystemExit(f"a stored search used the activity fallback; the plan assumed none: {fb}")
    inf = informative_from(results)
    out = {"informative": inf, "uninformative": sorted(set(results) - set(inf)), "by_lag": {}}
    for lag in (0, -52):
        rows = step_a_rows(results, diag3, inf, lag)
        res = step_a_rule(rows)
        res["rows"] = rows
        res["spearman_within_run"] = {
            run: float(spearmanr([r["m"] for r in rows if r["run"] == run],
                                 [r["gap"] for r in rows if r["run"] == run])[0])
            for run in ("measure", "cprime")}
        res["m_B"] = step_a_rows(results, diag3, inf, lag, half="B")
        res["uninformative"] = [
            {**row, "shortfall_B": results[row["cell"]][f"{row['run'] if row['run'] == 'measure' else 'rebuilt'}_run"]["shortfall_B"]}
            for row in step_a_rows(results, diag3, out["uninformative"], lag)]
        out["by_lag"][str(lag)] = res
    out["verdict"] = combine_lags(out["by_lag"])
    out_dir().mkdir(parents=True, exist_ok=True)
    (out_dir() / "step-a.json").write_text(json.dumps(out, indent=1))
    for lag, r in out["by_lag"].items():
        print(f"lag {lag}: agree {r['agree']}/{r['n']} {r['table']} C′ successes {r['cprime_successes_hit']} "
              f"failures {r['cprime_failures_hit']} -> {r['verdict']}; Spearman {r['spearman_within_run']}")
    print("step A:", out["verdict"])


def predictions(m_by_cell):
    """Experiment 3's pre-registered predictions: cell -> 'closes >= 50%' iff m_A > 0."""
    return {k: (None if m is None else bool(m > 0)) for k, m in m_by_cell.items()}


# --- leaks and rebuilds -------------------------------------------------------------------------

def leaks(band, net_fold, cell_fold, k3_fold_of, cache_bands):
    """True if a fold-`net_fold` network may not rebuild a cell of `band`: it is not the cell's
    own fold, or the band trained it (a cache band, or a K3 band, outside its left-out fold)."""
    if net_fold != cell_fold:
        return True
    trained = band in cache_bands or band in k3_fold_of
    return trained and k3_fold_of.get(band, -1) != net_fold


def networks(fold):
    """name -> (path, net fold, cache dirs) for the cell's fold."""
    d = home() / "learn/direc"
    base = ("cache", "cache-sw50r", "cache-ac20")
    nets = {"cprime-1h": (d / ("models-cprime-1h/fold2.pt" if fold == 2 else f"models-cprime-1h-f{fold}/fold{fold}.pt"),
                          fold, base)}
    if fold == 2:
        nets.update({"cprime-s1": (d / "models-cprime-s1/fold2.pt", 2, base),
                     "cprime-s2": (d / "models-cprime-s2/fold2.pt", 2, base),
                     "C": (d / "models-set3/fold2.pt", 2, base + ("cache-set3",)),
                     "R": (d / "models-resid/fold2.pt", 2, base),
                     "L": (d / "models-linear/fold2.pt", 2, base)})
    return nets


def _cache_bands(names):
    bands = set()
    for n in names:
        meta = home() / "learn/direc" / n / "meta.json"
        if meta.exists():
            bands |= {m["band"] for m in json.loads(meta.read_text())}
    return bands


def rebuild():
    """C′ 1-h (every cell) and the fold-2 extras (the torch interpreter, CPU), re-equalised to
    fold 2 as `song_settings.control_rebuild`."""
    import numpy as np
    import torch

    from learn import direc as D
    from learn import knob_ceiling as K
    from learn import song_settings as SS
    from learn import train as TR

    fo, ps = SS.folds(), K.parts()
    k3, _ = TR.k3_folds()
    avg = {f: np.load(SS.MODELS / "cache" / f"average-fold{f}.npy") for f in range(4)}
    log = {}
    for slug, amp in cells():
        band, f = ps[slug]["band"], fo[ps[slug]["band"]]
        dst = out_dir() / "rebuilt" / _tag(slug, amp)
        dst.mkdir(parents=True, exist_ok=True)
        fake = np.load(control_dir() / f"{_tag(slug, amp)}-fake.npy")
        for name, (path, nf, caches) in networks(f).items():
            key = f"{cell_key(slug, amp)}/{name}"
            if (dst / f"{name}.npy").exists():
                continue
            if leaks(band, nf, f, k3, _cache_bands(caches)):
                log[key] = "dropped: leak"
                continue
            try:
                net = D.load_model(path).eval()
                x = D.rebuild(net, fake.astype(np.float32), device=torch.device("cpu")).astype(np.float64)
            except Exception as e:                       # the existing load path must run unchanged
                log[key] = f"dropped: {type(e).__name__}: {e}"
                continue
            np.save(dst / f"{name}.npy", to_lufs(eq_to(x, avg[2] - avg[f])))
            log[key] = "ok"
            print(key, "ok", flush=True)
    (out_dir() / "rebuild-log.json").write_text(json.dumps(log, indent=1))


# --- build the variants -------------------------------------------------------------------------

def _sha(a):
    return hashlib.sha256(a.tobytes()).hexdigest()


def build_cell(slug, amp, idx, measure, cprime, other, extras):
    """name -> (array or None, meta) for one cell (the declared list, with drops recorded)."""
    out = {"base": (measure, {})}
    crest = {}
    for name, delta in CREST.items():
        y, meta = compress_to_crest(measure, delta)
        crest[name] = (y, meta)
    for name, (y, meta) in crest.items():
        if meta["reached"]:
            out[name] = (y, meta)
        elif name == "crest-5" and crest["crest-3"][1]["reached"]:
            out[name] = (y, {**meta, "note": "R = 10 at its lowest θ; achieved value recorded"})
        else:
            out[name] = (None, {**meta, "dropped": "unreachable"})
    out["placebo-smear"] = (placebo_smear(measure), {})
    for name, tau in SMEAR.items():
        out[name] = (envelope_smear(measure, tau), {})
    for name, g in SHELF.items():
        out[name] = (shelf(measure, g), {})
    for name, g in BELL.items():
        out[name] = (bell(measure, g), {})
    out["phase-scramble"] = (phase_scramble(measure, SEED + idx, measure), {"seed": SEED + idx})
    for name, db in BLEED.items():
        out[name] = (bleed(measure, other, db), {})
    out["cprime-env-swap"] = (envelope_swap(measure, cprime), {})
    out["cprime-spectrum"] = (spectrum_swap(measure, cprime), {})
    delta = crest_db(measure) - crest_db(cprime)
    if delta <= 0:
        out["cprime-crest"] = (None, {"dropped": "C′'s crest is not lower", "delta": delta})
    else:
        y, meta = compress_to_crest(measure, delta)
        out["cprime-crest"] = (y if meta["reached"] else None,
                               {**meta, "delta": delta, **({} if meta["reached"] else {"dropped": "unreachable"})})
    out["cprime"] = (cprime, {})
    rebq = oracle_eq(cprime, measure)
    out["cprime-oracle-eq"] = (rebq, {})
    out["transplant-5"] = (transplant(cprime, measure, 5.0), {})
    out["transplant-10"] = (transplant(cprime, measure, 10.0), {})
    out["cprime-eq-transplant-10"] = (transplant(rebq, measure, 10.0, eq_to_ref=True), {})
    for name in ("cprime-1h", *EXTRAS):
        if name in extras:
            out[name] = (extras[name], {})
        elif name == "cprime-1h":
            out[name] = (None, {"dropped": "not rebuilt (run `rebuild`)"})
    return out


def build_variants():
    import numpy as np

    from learn import confirm_run as CR
    from learn import knob_ceiling as K

    ps = K.parts()
    bp = bleed_part()
    other = K.measure_di(ps[bp])
    manifest = {"bleed_part": bp, "cells": {}}
    for idx, (slug, amp) in enumerate(cells()):
        key, tag = cell_key(slug, amp), _tag(slug, amp)
        measure = K.measure_di(ps[slug])
        raw = CR.mono(ps[slug]["crop"] / "di.wav")
        cprime = np.load(control_dir() / f"{tag}-rebuilt.npy")
        rdir = out_dir() / "rebuilt" / tag
        extras = {p.stem: np.load(p) for p in rdir.glob("*.npy")} if rdir.exists() else {}
        vdir = out_dir() / "variants" / tag
        vdir.mkdir(parents=True, exist_ok=True)
        cm = {}
        for name, (y, meta) in build_cell(slug, amp, idx, measure, cprime, other, extras).items():
            if y is None:
                cm[name] = {**meta, "rendered": False}
                continue
            lag = gcc_lag(y, raw, below_hz=1000 if name == "phase-scramble" else None)
            if abs(lag) > LAG_TOL or not np.all(np.isfinite(y)) or len(y) != len(measure):
                cm[name] = {**meta, "rendered": False, "dropped": f"lag check {lag}", "gcc_lag": lag}
                print(key, name, "stopped: lag", lag, flush=True)
                continue
            np.save(vdir / f"{name}.npy", y)
            env_m, env_y = _frames_db(measure), _frames_db(y)
            p = env_m >= env_m.max() - 40
            cm[name] = {**meta, "rendered": True, "sha256": _sha(np.asarray(y, np.float64)), "gcc_lag": lag,
                        "crest_change": crest_db(y) - crest_db(measure), "band_shifts": band_levels(y, measure),
                        "env_corr": float(np.corrcoef(env_y[p], env_m[p])[0, 1]),
                        "proxies": {w: proxies(y, measure, w) for w in WINDOWS}}
        manifest["cells"][key] = cm
        print(key, sum(v["rendered"] for v in cm.values()), "variants", flush=True)
    (out_dir() / "manifest.json").write_text(json.dumps(manifest, indent=1))


# --- render (step B) ----------------------------------------------------------------------------

def disk_ok():
    return shutil.disk_usage(pathlib.Path.home()).free / 1e9 >= MIN_FREE_GB


def renders_on_disk():
    d = out_dir() / "scores"
    return sum(json.loads(p.read_text()).get("renders", 0) for p in d.rglob("*.json")) if d.exists() else 0


def cap_ok(on_disk, n_shards):
    """Room for one more variant in every running shard."""
    return on_disk + RENDERS_PER_VARIANT * n_shards <= CAP


def render_order(manifest, shard):
    """(amp, slug, variant) for this shard: the repeat rows first, then the rest; grouped by amp."""
    cs = cells()[shard[0]::shard[1]]
    order = []
    for rows in (REPEAT_ROWS, None):
        for amp in ("pr12", "sw50r"):
            for slug, a in cs:
                if a != amp:
                    continue
                cm = manifest["cells"][cell_key(slug, a)]
                names = rows or [n for n in (*MEASURE_ROWS, *REAL_ROWS, *EXTRAS) if n not in REPEAT_ROWS]
                order += [(amp, slug, n) for n in names if cm.get(n, {}).get("rendered")]
    return order


def repeat_check(name, key, scores, results, diag3):
    """Rows 1, 19 and 21 against the stored figures, within 0.005 (log)."""
    if name == "base":
        ref, mask = {"S": results[key]["S"], "T": results[key]["target"]}, "measure"
    elif name == "cprime":
        ref, mask = {"S": diag3[key]["reb/S/lag0"], "T": diag3[key]["reb/T/lag0"]}, "v"
    elif name == "cprime-oracle-eq":
        ref, mask = {"S": diag3[key]["rebEQ/S/lag0"], "T": diag3[key]["rebEQ/T/lag0"]}, "v"
    else:
        return
    for st in ("S", "T"):
        for h in ("A", "B"):
            got = scores[mask][h][st]["d"]
            if got is None or abs(math.log(got / ref[st][h])) > 0.005:
                raise SystemExit(f"repeat check failed: {key} {name} {st} half {h}: {got} vs {ref[st][h]}")


def render(shard):
    import numpy as np

    from learn import knob_ceiling as K

    manifest = json.loads((out_dir() / "manifest.json").read_text())
    results, diag3 = load_results(), json.loads(DIAG3.read_text())
    ps = K.parts()
    rr = K.Renderer()                                   # isolate=True
    try:
        menu = rr.menu()
        for amp, slug, name in render_order(manifest, shard):
            key, tag = cell_key(slug, amp), _tag(slug, amp)
            f = out_dir() / "scores" / tag / f"{name}.json"
            if f.exists():
                continue
            if not disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            if not cap_ok(renders_on_disk(), shard[1]):
                raise SystemExit(f"render cap {CAP} reached")
            part = ps[slug]
            sel, S = menu[amp][K.START[part["gain_class"]][amp]]
            T = {tuple(k.rsplit("/", 1)): v for k, v in
                 json.loads((control_dir() / f"{tag}-target.json").read_text()).items()}
            fake = np.load(control_dir() / f"{tag}-fake.npy")
            v = np.load(out_dir() / "variants" / tag / f"{name}.npy")
            measure = K.measure_di(part)
            v32 = v.astype(np.float32)
            rr.render(v32, sel, S)                      # warm-up
            ys, yt = rr.render(v32, sel, S), rr.render(v32, sel, T)
            scores = {}
            for mask_name, mask in (("v", v), ("measure", measure)):
                scores[mask_name] = {}
                for w in WINDOWS:
                    row = {}
                    for st, y in (("S", ys), ("T", yt)):
                        d, fb, why = distance(fake, y, mask, 0, w)
                        row[st] = {"d": d, "fallback": fb, "reason": None if d is not None else why}
                    row["m"] = margin(row["S"]["d"], row["T"]["d"])
                    scores[mask_name][w] = row
            repeat_check(name, key, scores, results, diag3)
            f.parent.mkdir(parents=True, exist_ok=True)
            tmp = f.with_suffix(".tmp")
            tmp.write_text(json.dumps({"cell": key, "variant": name, "lag": 0, "renders": RENDERS_PER_VARIANT,
                                       "scores": scores}, indent=1))
            tmp.replace(f)
            print(key, name, {w: scores["measure"][w]["m"] for w in WINDOWS}, rr.count, flush=True)
    finally:
        rr.close()


# --- decisions ----------------------------------------------------------------------------------

def base_set(m, informative_cells):
    """Informative cells whose base margin is > 0 in this window and mask."""
    return {c for c in informative_cells if (m.get("base", {}).get(c) or 0) > 0}


def count_inversions(m, variant, informative_cells):
    """(inversions, n): m ≤ 0 among base-set cells where the variant is defined."""
    bs = base_set(m, informative_cells)
    vals = [m.get(variant, {}).get(c) for c in bs]
    vals = [x for x in vals if x is not None]
    return sum(x <= 0 for x in vals), len(vals)


def count_positive(m, variant, cells_):
    vals = [m.get(variant, {}).get(c) for c in cells_]
    vals = [x for x in vals if x is not None]
    return sum(x > 0 for x in vals), len(vals)


def d1(m, informative_cells):
    """D1, dynamics against tilt (thresholds declared for n = 9, rescaled by ceiling)."""
    p_inv, p_n = count_inversions(m, "placebo-smear", informative_cells)
    c_inv, c_n = count_inversions(m, "crest-3", informative_cells)
    s_inv, s_n = count_inversions(m, "cprime-spectrum", informative_cells)
    out = {"placebo": [p_inv, p_n], "crest-3": [c_inv, c_n], "cprime-spectrum": [s_inv, s_n],
           "dose": {v: list(count_inversions(m, v, informative_cells))
                    for v in ("crest-1.5", "crest-5", *SHELF, *BELL, *SMEAR, "cprime-crest", "cprime-env-swap")}}
    if p_inv > _ceil(1 / 9, p_n):
        return {**out, "reading": "undecided (placebo inverts > 1)"}
    if c_n < 5:
        return {**out, "reading": "undecided (crest -3 reached on < 5 cells)"}
    crest_holds = c_inv >= _ceil(1 / 2, c_n)
    if crest_holds and s_inv <= _ceil(1 / 9, s_n):
        r = "dynamics confirmed"
    elif crest_holds:
        r = "dynamics and tilt"
    elif s_inv >= _ceil(1 / 2, s_n):
        r = "tilt, not dynamics"
    else:
        r = "neither"
    return {**out, "reading": r}


def d2(m, informative_cells):
    """D2: a transplant restores if m > 0 on ≥ two-thirds of the base set and on more cells than C′."""
    bs = base_set(m, informative_cells)
    out = {}
    for t in TRANSPLANTS:
        on = [c for c in bs if m.get(t, {}).get(c) is not None]
        pos, n = count_positive(m, t, on)
        c_pos, _ = count_positive(m, "cprime", on)
        out[t] = {"positive": pos, "n": n, "cprime_positive": c_pos,
                  "restores": n > 0 and pos >= _ceil(2 / 3, n) and pos > c_pos}
    if out["transplant-5"]["restores"] or out["transplant-10"]["restores"]:
        r = "plain transplant restores"
    elif out["cprime-eq-transplant-10"]["restores"]:
        r = "only the oracle-EQ transplant restores"
    else:
        r = "none restores"
    return {**out, "reading": r}


def within_cell_rho(proxy_by_variant, m_by_variant):
    """Spearman ρ across a cell's variants (both defined); None with < 3 points or constant."""
    from scipy.stats import spearmanr

    vs = [v for v in proxy_by_variant if proxy_by_variant[v] is not None and m_by_variant.get(v) is not None]
    if len(vs) < 3:
        return None
    a, b = [proxy_by_variant[v] for v in vs], [m_by_variant[v] for v in vs]
    if len(set(a)) < 2 or len(set(b)) < 2:
        return None
    return float(spearmanr(a, b)[0])


def _band_means(rho_by_cell, band_of):
    by = {}
    for c, r in rho_by_cell.items():
        if r is not None and not math.isnan(r):
            by.setdefault(band_of[c], []).append(r)
    return {b: sum(v) / len(v) for b, v in by.items()}


def d3(rho, band_of, seed=BOOT_SEED, draws=BOOT_DRAWS):
    """rho: proxy -> cell -> within-cell ρ. Band-weighted mean, band-clustered bootstrap 90%
    interval, the paired difference against coherence, bands beating coherence, adoption."""
    import numpy as np

    coh = _band_means(rho["coherence"], band_of)
    rng = np.random.default_rng(seed)
    out = {}
    for p in rho:
        bm = _band_means(rho[p], band_of)
        bands = sorted(bm)
        if not bands:
            out[p] = {"rho": None}
            continue
        vals = np.array([bm[b] for b in bands])
        idx = rng.integers(0, len(bands), (draws, len(bands)))
        boot = vals[idx].mean(1)
        res = {"rho": float(vals.mean()), "lo90": float(np.percentile(boot, 5)),
               "hi90": float(np.percentile(boot, 95)), "bands": len(bands)}
        if p != "coherence":
            shared = [b for b in bands if b in coh]
            diff = np.array([bm[b] - coh[b] for b in shared])
            if len(shared):
                j = rng.integers(0, len(shared), (draws, len(shared)))
                res["diff_lo90"] = float(np.percentile(diff[j].mean(1), 5))
            else:
                res["diff_lo90"] = None
            res["bands_beating_coherence"] = [int((diff > 0).sum()), len(shared)]
            res["passes"] = (p not in BASELINES and res["rho"] >= 0.6 and res["diff_lo90"] is not None
                             and res["diff_lo90"] > 0 and int((diff > 0).sum()) >= 5)
        out[p] = res
    passing = [p for p in out if out[p].get("passes")]
    adopted = max(passing, key=lambda p: out[p]["rho"]) if passing else None
    return {"proxies": out, "adopted": adopted, "passing": passing}


# --- report -------------------------------------------------------------------------------------

def load_scores():
    """(window, mask) -> variant -> cell -> m."""
    out = {}
    for p in (out_dir() / "scores").rglob("*.json"):
        s = json.loads(p.read_text())
        for mask in MASKS:
            for w in WINDOWS:
                out.setdefault((w, mask), {}).setdefault(s["variant"], {})[s["cell"]] = s["scores"][mask][w]["m"]
    return out


def rho_table(manifest, m, variants_filter=None, window="full"):
    rho = {p: {} for p in PROXIES}
    for c, cm in manifest["cells"].items():
        vs = [v for v, meta in cm.items() if meta.get("rendered") and (variants_filter is None or variants_filter(v))]
        mv = {v: m.get(v, {}).get(c) for v in vs}
        for p in PROXIES:
            rho[p][c] = within_cell_rho({v: cm[v]["proxies"][window][p] for v in vs}, mv)
    return rho


def report():
    from learn import knob_ceiling as K

    ps = K.parts()
    manifest = json.loads((out_dir() / "manifest.json").read_text())
    sc = load_scores()
    inf = informative()
    band_of = {cell_key(s, a): ps[s]["band"] for s, a in cells()}
    primary = ("full", "measure")
    out = {"informative": inf, "renders": renders_on_disk()}
    readings = {}
    for w in WINDOWS:
        for mask in MASKS:
            m = sc.get((w, mask), {})
            readings[f"{w}/{mask}"] = {"D1": d1(m, inf), "D2": d2(m, inf)}
    out["D1"], out["D2"] = readings["full/measure"]["D1"], readings["full/measure"]["D2"]
    lobo = {}
    for b in sorted(set(band_of.values())):
        keep = [c for c in inf if band_of[c] != b]
        m = sc.get(primary, {})
        lobo[b] = {"D1": d1(m, keep)["reading"], "D2": d2(m, keep)["reading"]}
    for d in ("D1", "D2"):
        alt = {k: v[d]["reading"] for k, v in readings.items()} | {f"without {b}": v[d] for b, v in lobo.items()}
        out[d]["fragile_under"] = sorted(k for k, r in alt.items() if r != out[d]["reading"])
    m_v = sc.get(("full", "v"), {})
    out["D3"] = d3(rho_table(manifest, m_v), band_of)
    out["D3_without_pure_eq"] = d3(rho_table(manifest, m_v, lambda v: v not in PURE_EQ), band_of)
    out["D3_real_only"] = d3(rho_table(manifest, m_v, lambda v: v in REAL_ONLY), band_of)
    out["D3_informative_only"] = d3({p: {c: r for c, r in t.items() if c in inf}
                                     for p, t in rho_table(manifest, m_v).items()}, band_of)
    out["per_part"] = {}
    for (w, mask), m in sc.items():
        if (w, mask) != primary:
            continue
        for v, by in m.items():
            for c, x in by.items():
                slug, amp = c.split("|")
                out["per_part"].setdefault(slug, {}).setdefault(v, {})[amp] = x
    out["readings"] = readings
    (out_dir() / "report.json").write_text(json.dumps(out, indent=1))
    print("D1:", out["D1"]["reading"], "fragile under", out["D1"]["fragile_under"])
    print("D2:", out["D2"]["reading"], "fragile under", out["D2"]["fragile_under"])
    print("D3 adopted:", out["D3"]["adopted"], "passing", out["D3"]["passing"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("step-a", "rebuild", "build-variants", "render", "report"))
    ap.add_argument("--shard", default="0/1")
    a = ap.parse_args(argv)
    i, n = (int(x) for x in a.shard.split("/"))
    {"step-a": step_a, "rebuild": rebuild, "build-variants": build_variants,
     "render": lambda: render((i, n)), "report": report}[a.step]()


if __name__ == "__main__":
    main()
