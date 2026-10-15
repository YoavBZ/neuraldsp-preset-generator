"""DI-recovery experiment 4: C′'s successor for fine structure (`docs/di-fine-structure-plan.md`).

The step-0 tools, the per-arm known-target control runners, the leak check, and the declared
readouts. Training is `learn.direc fit` with its experiment-4 flags. Outputs go under
`~/ndsp-presets/learn/di-fine-structure/`; the stored control (`song-settings/armA-control`) is
only ever read.

Interpreters: MAIN = the main `.venv` (renders, numpy), TORCH = `~/ndsp-presets/tools/demucs-venv`,
DAC = `~/ndsp-presets/tools/dac-venv`. Run order (the plan's machine order):

    # step 0 (CPU)
    MAIN  -m learn.di_fine_structure reads                 # 0a: report.json, gap spectra, disk
    TORCH -m learn.di_fine_structure gate                  # 0a: C′'s dec.0 gate per fold (PR12 cache)
    MAIN  -m learn.di_fine_structure d0                    # 0b: D0, 48 renders (+1 warm-up)
    TORCH -m learn.di_fine_structure idem-rebuild          # 0b: x̂₂ = C′(A_T(x̂))
    MAIN  -m learn.di_fine_structure idem-render           # 0b: 24 renders
    MAIN  -m learn.di_fine_structure swap                  # 0b: 36 renders
    MAIN  -m learn.di_fine_structure dac-prep              # 0c
    DAC   learn/dac_roundtrip.py --inp …/dac/in --out …/dac/out
    MAIN  -m learn.di_fine_structure dac-render            # 0c: 48 renders; the E1′ reading
    # 0d (after the cache rebuild): `learn.direc fit --calibrate 50 …`, then
    MAIN  -m learn.di_fine_structure weights --stage 1a --calibration DIR
    MAIN  -m learn.di_fine_structure weights --stage 1b --calibration DIR
    # 0e: two `fit --overfit 8` runs (1b's loss, and C′'s alone), then
    MAIN  -m learn.di_fine_structure capacity --run DIR --ref DIR [--head DIR]
    # step 1: `fit` per arm; 1d: `fit --eval-only` per arm and for C′, `cprime_folds check`, then
    MAIN  -m learn.di_fine_structure screen --fold 3 --cprime DIR --arm 1a=DIR …
    # step 2, per rendered arm
    TORCH -m learn.di_fine_structure control-rebuild --arm 1a --folds 3
    MAIN  -m learn.di_fine_structure control-search --arm 1a --folds 3 [--shard i/n]
    MAIN  -m learn.di_fine_structure step2 --arms 1a 1b 1c [--z]
    # fold-1 branch (user's yes), step 4
    MAIN  -m learn.di_fine_structure fold1 --arms …
    MAIN  -m learn.di_fine_structure step4 --arm WINNER
    MAIN  -m learn.di_fine_structure tally
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import shutil
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

SR = 48000
LATENCY = 52                              # Morgan's render latency
HOME = pathlib.Path("~/ndsp-presets").expanduser()
MODELS = HOME / "learn/direc"
CACHES = ("cache", "cache-sw50r", "cache-ac20")
ARMS = ("1z", "1a", "1b", "1c", "1e")
TIE_ORDER = ("1z", "1a", "1b", "1e", "1c")     # cheapest first (step 2)
EPS = 1e-9
WITHIN = 0.03                             # amendment 2's "within 0.03" (one-sided)
CLOSE = 0.5
BUDGET_SEARCH = 150
SEED_A = 20261013
LAG_TOL = 3
MIN_FREE_GB = 31.0
RENDER_CAP = 11_100                       # the plan's budgeted maximum; branches need the user's yes
CHECK2_FLOOR = 0.1126
VAL_MARGIN = 0.02
HF_MARGIN_DB = 2.0
TRIM_S = 0.25                             # the isolate fade-in: zeroed before any audio use
SHARE_RANGES = {"short": (0.15, 0.40), "peak": (0.05, 0.15), "gap": (0.03, 0.10)}
PHASE_RANGE = (0.15, 0.45)                # 0.3 × (short-window + mrstft) ± 50%
PROVISIONAL = {"short": 1.0, "peak": 0.1, "gap": 0.02, "phase": 1.0}


def root():
    return HOME / "learn/di-fine-structure"


def control_dir():
    return HOME / "learn/song-settings/armA-control"


def arm_dir(arm):
    """Each arm's control outputs; never inside the stored control (amendment 4: skip-if-exists)."""
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}")
    d = root() / "control" / arm
    c = control_dir()
    assert d != c and c not in d.parents and d not in c.parents
    return d


def net_path(arm, fold):
    return MODELS / f"models-fs-{arm}-f{fold}" / f"fold{fold}.pt"


def _tag(slug, amp):
    return f"{slug}-{amp}"


def _key(slug, amp):
    return f"{slug}|{amp}"


def _atomic(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    tmp.replace(path)


def disk_ok():
    return shutil.disk_usage(pathlib.Path.home()).free / 1e9 >= MIN_FREE_GB


# --- the stored control -------------------------------------------------------------------------

def cells():
    from learn import song_settings as SS

    return SS.control_cells()


def cell_folds():
    """key -> the song-settings fold of the cell's band."""
    from learn import knob_ceiling as K
    from learn import song_settings as SS

    ps, fo = K.parts(), SS.folds()
    return {_key(s, a): fo[ps[s]["band"]] for s, a in cells()}


def stored_results(d=None):
    d = d or control_dir()
    return {_key(s, a): json.loads((d / f"{_tag(s, a)}-result.json").read_text()) for s, a in cells()}


def informative(stored):
    """Amendment 2: d_S − d_target ≥ 0.1 on half B through the measure DI."""
    return sorted(k for k, r in stored.items() if r["S"]["B"] - r["target"]["B"] >= 0.1 - EPS)


# --- the declared rules -------------------------------------------------------------------------

def _finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def run_summary(stored, keys, found):
    """(closed ≥ 50%, mean shortfall over finite cells, n) for a run's half-B distances
    `found[key]`, against the stored S and target."""
    closed, short = 0, []
    for k in keys:
        s, t, f = stored[k]["S"]["B"], stored[k]["target"]["B"], found[k]
        if _finite(f) and s != t and (s - f) / (s - t) >= CLOSE - EPS:
            closed += 1
        if _finite(f) and f > 0 and t > 0:
            short.append(math.log(f / t))
    return {"closed": closed, "mean_shortfall": sum(short) / len(short) if short else None,
            "n": len(keys), "finite": len(short)}


def subset_rule(stored, keys, arm_found):
    """Step 2's rule on `keys` (fold 3's 4 informative cells, or the fold-1 branch's 7), built as
    amendment 2's row 2 on the subset (plan, The gate):
    go: closed ≥ 2/3 of n, or mean shortfall ≤ the measure-DI run's + 0.03;
    stop: (not go and) mean shortfall > C′'s − 0.03; otherwise undecided."""
    meas = run_summary(stored, keys, {k: stored[k]["measure_run"]["B"] for k in keys})
    cp = run_summary(stored, keys, {k: stored[k]["rebuilt_run"]["B"] for k in keys})
    arm = run_summary(stored, keys, arm_found)
    n, m = arm["n"], arm["mean_shortfall"]
    need = math.ceil(2 * n / 3 - EPS)
    if arm["finite"] < n:
        reading = "undecided (a refused or missing cell)"
    elif arm["closed"] >= need or m <= meas["mean_shortfall"] + WITHIN + EPS:
        reading = "go"
    elif m > cp["mean_shortfall"] - WITHIN + EPS:
        reading = "stop"
    else:
        reading = "undecided"
    return {"reading": reading, "arm": arm, "measure_run": meas, "cprime": cp, "need_closed": need,
            "go_shortfall": meas["mean_shortfall"] + WITHIN, "stop_shortfall": cp["mean_shortfall"] - WITHIN}


def beats_1z(arm, z):
    """An arm goes ahead of 1z only if it closes more cells, or its mean shortfall is ≥ 0.03 lower."""
    return arm["closed"] > z["closed"] or (
        arm["mean_shortfall"] is not None and z["mean_shortfall"] is not None
        and arm["mean_shortfall"] <= z["mean_shortfall"] - WITHIN + EPS)


def choose(readings, z=None):
    """readings: arm -> subset_rule output (arms other than 1z); z: 1z's, if rendered.
    -> {"outcome": "go"|"fold-1 branch"|"stop", "winner", "undecided", "note"}."""
    goers = [a for a, r in readings.items() if r["reading"] == "go"]
    undecided = sorted(a for a, r in readings.items() if r["reading"].startswith("undecided"))
    if not goers:
        if undecided:
            return {"outcome": "fold-1 branch", "winner": None, "undecided": undecided,
                    "note": "only the undecided arms take it; it needs the user's yes"}
        return {"outcome": "stop", "winner": None, "undecided": [],
                "note": "every arm stops: the loss route failed on fold 3"}
    note = ""
    if z is not None:
        if z["reading"] == "go":
            note = "1z meets the go row: gains are put down to fine-tuning"
        ahead = [a for a in goers if beats_1z(readings[a]["arm"], z["arm"])]
        if not ahead:
            return {"outcome": "go", "winner": "1z", "undecided": [],
                    "note": (note + "; " if note else "") + "no arm beats 1z: the terms are not shown"}
        goers = ahead
    rank = sorted(goers, key=lambda a: (-readings[a]["arm"]["closed"], readings[a]["arm"]["mean_shortfall"],
                                         TIE_ORDER.index(a)))
    return {"outcome": "go", "winner": rank[0], "undecided": [], "note": note}


def step4(stored, arm_results):
    """The gate: song_readout's control function on the 12 cells, the arm's rebuilt run in place
    of C′'s; plus the 5 non-fold-3 informative cells apart (descriptive)."""
    from learn import song_readout as SR_

    rows = []
    for k, r in stored.items():
        if k not in arm_results:
            raise SystemExit(f"step 4: no result for {k}")
        rows.append({**r, "rebuilt_run": arm_results[k]["rebuilt_run"]})
    out = SR_.known_target_control(rows)
    return out


def share_rule(means, provisional, fixed=None):
    """Step 0d's pre-registered rule. For 1a's terms: share = w·term / L_C′; for 1b's phase
    term: share = w·phase / (w_short·short + mrstft), with 1a's final weights `fixed`. A weight
    whose share lies in its range is kept; otherwise it becomes the range's midpoint, rounded to
    one significant figure."""
    out = {"weights": {}, "shares": {}, "kept": {}}
    for k, w in provisional.items():
        if k == "phase":
            den = fixed["short"] * means["short"] + means["mrstft"]
            lo, hi = PHASE_RANGE
        else:
            den = means["L_C"]
            lo, hi = SHARE_RANGES[k]
        share = w * means[k] / den
        kept = lo - EPS <= share <= hi + EPS
        w2 = w if kept else float(f"{(lo + hi) / 2 * den / means[k]:.1g}")
        out["weights"][k], out["shares"][k], out["kept"][k] = w2, share, kept
    return out


def capacity_verdict(run, ref):
    """Step 0e on the 8 crops' end metrics: in-loss (1-ms and 2.5-ms crest within 1 dB, gap level
    within 3 dB; quiet frames stand in when the crops have no gap frame) and out-of-loss
    (0.5-ms crest within 1 dB, SNR ≥ 3 dB above the C′-loss run). Memorisation only."""
    gap = run["gap_db"] if run.get("gap_db") is not None else run.get("quiet_db")
    checks = {"crest_1ms": abs(run["crest_1ms_err"]) <= 1.0,
              "crest_2.5ms": abs(run["crest_2.5ms_err"]) <= 1.0,
              "gap": gap is not None and abs(gap) <= 3.0,
              "crest_0.5ms": abs(run["crest_0.5ms_err"]) <= 1.0,
              "snr": run["snr_db"] >= ref["snr_db"] + 3.0}
    return {"pass": all(checks.values()), "checks": checks,
            "gap_source": "gap" if run.get("gap_db") is not None else "quiet"}


def screen_verdict(arm_eval, cprime_eval, check2):
    """Step 1d. Hard stops are breakage guards only: validation ratio above C′'s + 0.02, check 2
    below 0.1126, 3–8 kHz more than 2 dB above C′'s. Crest and gap are reported."""
    a, c = arm_eval["fine"], cprime_eval["fine"]
    stops = {"val_ratio": arm_eval["ratio"] > cprime_eval["ratio"] + VAL_MARGIN + EPS,
             "check2": check2 is None or check2 < CHECK2_FLOOR - EPS,
             "hf_3_8k": a["hf_3_8k_db"] - c["hf_3_8k_db"] > HF_MARGIN_DB + EPS}
    report = {k: a[k] for k in a if k.endswith("_err") or k in ("gap_db", "quiet_db", "snr_db", "hf_3_8k_db")}
    return {"passes": not any(stops.values()), "stops": stops, "ratio": arm_eval["ratio"],
            "cprime_ratio": cprime_eval["ratio"], "check2": check2, "report": report}


def parent_of_1c(eval_1a, eval_1b):
    """The better of 1a and 1b by the 1-ms crest error; within 0.2 dB goes to 1a."""
    ea, eb = abs(eval_1a["fine"]["crest_1ms_err"]), abs(eval_1b["fine"]["crest_1ms_err"])
    return "1b" if eb < ea - 0.2 - EPS else "1a"


def render_set(verdicts, evals):
    """Arms rendered without the user's yes: 1a, 1b, and the better of 1c and 1e by the 1-ms crest
    error, among arms with no breakage stop. -> (rendered, needs the user's yes)."""
    ok = [a for a in ("1a", "1b", "1c", "1e") if a in verdicts and verdicts[a]["passes"]]
    pick = [a for a in ("1a", "1b") if a in ok]
    late = [a for a in ("1c", "1e") if a in ok]
    if late:
        best = min(late, key=lambda a: (abs(evals[a]["fine"]["crest_1ms_err"]), TIE_ORDER.index(a)))
        pick.append(best)
        rest = [a for a in late if a != best]
    else:
        rest = []
    return pick, rest


def e1_opens(m_q9, m_true, crest1_err_q9, keys):
    """0c: E1′ opens only if the 9-codebook round trip keeps m > 0 on every fold-3 informative
    cell, a mean m ≥ 0.75 × the true DI's (as scored in 0c), and a 1-ms crest within 1 dB."""
    if any(m_q9.get(k) is None or m_true.get(k) is None for k in keys):
        return {"opens": False, "why": "a cell is missing (lag check or refusal)"}
    mq = sum(m_q9[k] for k in keys) / len(keys)
    mt = sum(m_true[k] for k in keys) / len(keys)
    crest = max(abs(crest1_err_q9[k]) for k in keys)
    ok = all(m_q9[k] > 0 for k in keys) and mq >= 0.75 * mt - EPS and crest <= 1.0 + EPS
    return {"opens": ok, "mean_m_q9": mq, "mean_m_true": mt, "bar": 0.75 * mt, "max_crest1_err": crest}


def swap_reorders(m_truemag, m_truephase, keys):
    """0b's swap rung moves 1b ahead of 1a only if the true phase restores m > 0 on ≥ 6 of 9
    and the true magnitude on ≤ 3."""
    pos = lambda m: sum(1 for k in keys if m.get(k) is not None and m[k] > 0)  # noqa: E731
    return {"true_phase_positive": pos(m_truephase), "true_magnitude_positive": pos(m_truemag),
            "1b_first": pos(m_truephase) >= 6 and pos(m_truemag) <= 3}


# --- leaks ----------------------------------------------------------------------------------------

def train_pool_bands(fold, cache_dirs, k3=None, crops=None):
    """The bands a fold-`fold` network trained on, exactly as `direc.fit` splits: every cache
    row whose band is not in K3 fold `fold` (bands outside K3 train every fold), plus the bands
    of the training folds' bleed backings."""
    from learn import direc as D
    from learn import train as TR

    fold_of, band_of = k3 or TR.k3_folds()
    crops = crops or D.CROPS
    pool = set()
    for c in cache_dirs:
        for m in json.loads((pathlib.Path(c) / "meta.json").read_text()):
            if fold_of.get(m["band"], -1) != fold:
                pool.add(m["band"])
    for part, b in band_of.items():
        if fold_of[b] != fold and (pathlib.Path(crops) / part / "backing_instrumental.wav").exists():
            pool.add(b)
    return pool


def assert_no_leak(band, net_fold, cell_fold, pool):
    if net_fold != cell_fold:
        raise AssertionError(f"network fold {net_fold} is not the cell's fold {cell_fold}")
    if band in pool:
        raise AssertionError(f"leak: band {band!r} is in the fold-{net_fold} network's training pool")


# --- the per-arm control runners (step 2, the fold-1 branch, step 4) ------------------------------

def _raw_di(part):
    from learn import confirm_run as CR

    return CR.mono(part["crop"] / "di.wav")


def control_rebuild(arm, folds):
    """The arm's fold networks rebuild the control fakes (CPU), re-equalised by (fold 2's average −
    fold f's), at −22.9 LUFS, with the ±3-sample lag check against the raw DI (TORCH)."""
    import numpy as np
    import torch

    from learn import direc as D
    from learn import knob_ceiling as K
    from learn import rank_margin as RM
    from learn import song_settings as SS
    from learn.direc_check import eq_to, to_lufs

    ps, fo = K.parts(), SS.folds()
    avg = {f: np.load(MODELS / "cache" / f"average-fold{f}.npy") for f in range(4)}
    d = arm_dir(arm)
    d.mkdir(parents=True, exist_ok=True)
    log_path = d / "rebuild-log.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {}
    nets = {}
    for slug, amp in cells():
        band = ps[slug]["band"]
        f = fo[band]
        if f not in folds or (d / f"{_tag(slug, amp)}-rebuilt.npy").exists():
            continue
        path = net_path(arm, f)
        if not SS.net_ready(path):
            raise SystemExit(f"{path} is not final (no DONE marker)")
        cfg = json.loads((path.parent / "config.json").read_text()) if (path.parent / "config.json").exists() else {}
        caches = [pathlib.Path(c) for c in cfg.get("caches", [MODELS / c for c in CACHES])]
        assert_no_leak(band, cfg.get("fold", f), f, train_pool_bands(f, caches))
        if f not in nets:
            nets[f] = D.load_model(path).eval()
        fake = np.load(control_dir() / f"{_tag(slug, amp)}-fake.npy")
        x = D.rebuild(nets[f], fake.astype(np.float32), device=torch.device("cpu")).astype(np.float64)
        y = to_lufs(eq_to(x, avg[2] - avg[f]))
        lag = RM.gcc_lag(y, _raw_di(ps[slug]))
        np.save(d / f"{_tag(slug, amp)}-rebuilt.npy", y)
        log[_key(slug, amp)] = {"fold": f, "network": str(path), "gcc_lag": lag, "lag_ok": abs(lag) <= LAG_TOL}
        print(slug, amp, "fold", f, "lag", lag, flush=True)
        _atomic(log_path, log)


def _held(rr, fake, di, sel, x):
    from learn import knob_ceiling as K

    return K.judge(fake, rr.render(di.astype("float32"), sel, x), di, 0)


def control_search(arm, folds, shard=(0, 1), cap=RENDER_CAP):
    """The rebuilt run only (150 renders, half A, `rebuilt_distance` at lag 0), the best judged
    through the measure DI on half B, and the margin (S and T through the rebuild). The stored
    S, target and measure-DI run are copied from `armA-control`, never re-rendered (MAIN)."""
    import numpy as np

    from learn import knob_ceiling as K
    from learn import rank_margin as RM
    from learn import song_settings as SS
    from learn.rebuilt_judge import rebuilt_distance

    ps, fo = K.parts(), SS.folds()
    d = arm_dir(arm)
    log = json.loads((d / "rebuild-log.json").read_text())
    stored = stored_results()
    rr = K.Renderer()
    try:
        menu = rr.menu()
        for slug, amp in [c for c in cells() if fo[ps[c[0]]["band"]] in folds][shard[0]::shard[1]]:
            key, tag = _key(slug, amp), _tag(slug, amp)
            f = d / f"{tag}-result.json"
            if f.exists():
                continue
            if not log.get(key, {}).get("lag_ok"):
                print(key, "skipped: no rebuild or lag check failed", flush=True)
                continue
            if not disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            if tally()["total"] + BUDGET_SEARCH + 3 > cap:
                raise SystemExit(f"render cap {cap} reached: going on needs the user's yes")
            part = ps[slug]
            sel, S = menu[amp][K.START[part["gain_class"]][amp]]
            fake = np.load(control_dir() / f"{tag}-fake.npy")
            rebuilt = np.load(d / f"{tag}-rebuilt.npy")
            di, r32 = K.measure_di(part), rebuilt.astype(np.float32)
            n0, counter = rr.count, {"fallback": 0}

            def objective(x):
                a, b = K.R.HALVES["A"]
                dd, proxy = rebuilt_distance(fake, rr.render(r32, sel, x), rebuilt, start_s=a, end_s=b, lag=0)
                counter["fallback"] += int(proxy)
                return math.inf if dd.distance is None else dd.distance

            x2, _, _, _ = K.knob_search(K.space(amp, S), S, objective, BUDGET_SEARCH, SEED_A)
            run = _held(rr, fake, di, sel, x2)
            st, tg = stored[key]["S"]["B"], stored[key]["target"]["B"]
            run["gap_closed_B"] = (st - run["B"]) / (st - tg) if st != tg else None
            run["shortfall_B"] = math.log(run["B"] / tg) if _finite(run["B"]) else None
            target = {tuple(k.rsplit("/", 1)): v for k, v in
                      json.loads((control_dir() / f"{tag}-target.json").read_text()).items()}
            ys, yt = rr.render(r32, sel, S), rr.render(r32, sel, target)
            margin = {}
            for mname, mask in (("v", rebuilt), ("measure", di)):
                ds, dt = RM.distance(fake, ys, mask, 0, "full")[0], RM.distance(fake, yt, mask, 0, "full")[0]
                margin[mname] = {"S": ds, "T": dt, "m": RM.margin(ds, dt)}
            res = {"arm": arm, "network": log[key]["network"], "lag": 0, "target": stored[key]["target"],
                   "S": stored[key]["S"], "measure_run": stored[key]["measure_run"], "rebuilt_run": run,
                   "fallback": counter["fallback"], "margin": margin, "renders": rr.count - n0,
                   "settings": {f"{m}/{k}": v for (m, k), v in x2.items()}}
            _atomic(f, res)
            print(key, arm, "gap closed", round(run["gap_closed_B"] or 0, 3), "renders", rr.count - n0, flush=True)
    finally:
        rr.close()


def arm_results(arm):
    d = arm_dir(arm)
    out = {}
    for s, a in cells():
        f = d / f"{_tag(s, a)}-result.json"
        if f.exists():
            out[_key(s, a)] = json.loads(f.read_text())
    return out


def subset_reading(arm, keys, stored):
    res = arm_results(arm)
    missing = [k for k in keys if k not in res]
    if missing:
        raise SystemExit(f"{arm}: no result for {missing}")
    return subset_rule(stored, keys, {k: res[k]["rebuilt_run"]["B"] for k in keys})


def readout(arms, folds, with_z, name):
    stored = stored_results()
    fo = cell_folds()
    keys = [k for k in informative(stored) if fo[k] in folds]
    readings = {a: subset_reading(a, keys, stored) for a in arms if a != "1z"}
    z = subset_reading("1z", keys, stored) if with_z else None
    out = {"cells": keys, "readings": readings, "1z": z, "choice": choose(readings, z)}
    _atomic(root() / f"{name}.json", out)
    for a, r in readings.items():
        print(a, r["reading"], r["arm"], flush=True)
    print("choice", out["choice"], flush=True)
    return out


# --- step 0a ---------------------------------------------------------------------------------------

def _band_db(x, edges, n=1024, mask=None):
    import numpy as np

    from analysis.aligned import _frames

    F = _frames(np.asarray(x, np.float64), n) * np.hanning(n)
    S = np.abs(np.fft.rfft(F, axis=1)) ** 2
    if mask is not None:
        S = S[mask[:len(S)]]
    f = np.fft.rfftfreq(n, 1 / SR)
    return np.array([10 * np.log10(S[:, (f >= a) & (f < b)].mean() + 1e-20) for a, b in zip(edges[:-1], edges[1:])])


def gap_spectra(measure, fake, reb, below_db=20.0):
    """Report only: on the measure DI's quiet frames (≥ 20 dB under its loudest, 1024-sample
    frames), C′'s excess over the true DI per band against the fake's; a high correlation means
    pass-through, a flat excess an error floor."""
    import numpy as np

    from analysis.aligned import _frames

    m = np.asarray(measure, np.float64)
    lv = 10 * np.log10((_frames(m, 1024) ** 2).mean(1) + 1e-20)
    quiet = lv < lv.max() - below_db
    if quiet.sum() < 4:
        return {"quiet_frames": int(quiet.sum()), "reading": None}
    edges = np.geomspace(100, 10000, 25)
    norm = lambda x: np.asarray(x, np.float64) / (np.sqrt(np.mean(np.asarray(x, np.float64) ** 2)) + 1e-12)  # noqa: E731
    bm, bf, br = (_band_db(norm(x), edges, mask=quiet) for x in (m, fake, reb))
    ex, fx = br - bm, bf - bm
    return {"quiet_frames": int(quiet.sum()), "excess_mean_db": float(ex.mean()), "excess_std_db": float(ex.std()),
            "corr_with_fake": float(np.corrcoef(ex, fx)[0, 1])}


def reads():
    """0a's zero-cost reads (MAIN)."""
    import numpy as np

    from learn import knob_ceiling as K

    rep = json.loads((HOME / "learn/rank-margin/report.json").read_text())
    pp, inf = rep["per_part"], [k.split("|") for k in rep["informative"]]
    rungs = {}
    for v in ("base", "cprime", "phase-scramble", "bleed-20", "bleed-10"):
        ms = {f"{p}|{a}": pp[p][v].get(a) for p, a in inf}
        vals = [m for m in ms.values() if m is not None]
        rungs[v] = {"per_cell": ms, "inverted": sum(m <= 0 for m in vals), "n": len(vals),
                    "mean_m": sum(vals) / len(vals) if vals else None}
    ps = K.parts()
    gaps = {}
    for s, a in cells():
        tag = _tag(s, a)
        gaps[_key(s, a)] = gap_spectra(K.measure_di(ps[s]), np.load(control_dir() / f"{tag}-fake.npy"),
                                       np.load(control_dir() / f"{tag}-rebuilt.npy"))
    out = {"rungs": rungs, "gap_spectra": gaps,
           "free_gb": shutil.disk_usage(pathlib.Path.home()).free / 1e9}
    _atomic(root() / "step0" / "reads.json", out)
    print(json.dumps({k: {x: v[x] for x in ("inverted", "n", "mean_m")} for k, v in rungs.items()}), flush=True)
    print("free GB", round(out["free_gb"], 1), flush=True)


def gate():
    """0a: `gate_open` of each fold's C′ on 96 of its validation rows from the PR12 cache (the
    SW50R and AC20 rows were deleted after the fold runs), centre crops at std 0.1 (TORCH)."""
    import numpy as np
    import torch

    from learn import direc as D
    from learn import song_settings as SS
    from learn import train as TR

    fold_of, _ = TR.k3_folds()
    cache = MODELS / "cache"
    meta = json.loads((cache / "meta.json").read_text())
    X = np.load(cache / "input.npy", mmap_mode="r")
    out = {}
    for f in range(4):
        rows = [i for i, m in enumerate(meta) if fold_of.get(m["band"], -1) == f]
        idx = np.random.default_rng(0).choice(rows, min(96, len(rows)), replace=False)
        a = (D.CLIP - D.CROP) // 2
        xs = [X[i][a:a + D.CROP].astype(np.float32) / 32767 for i in idx]
        x = torch.tensor(np.stack([v / (v.std() + 1e-9) * 0.1 for v in xs]))[:, None]
        net = D.load_model(SS.cprime(f)).eval()
        g = [D.gate_open(net, x[s:s + 12]) for s in range(0, len(x), 12)]
        out[str(f)] = float(np.mean(g))
        print("fold", f, "gate", round(out[str(f)], 3), flush=True)
    _atomic(root() / "step0" / "gate.json", out)


# --- step 0b ----------------------------------------------------------------------------------------

def save_render(path, y):
    """16-bit FLAC, peak-normalised; the peak goes in a JSON beside it."""
    import numpy as np
    import soundfile as sf

    peak = float(np.abs(y).max()) + 1e-12
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.asarray(y, np.float64) / peak * 0.99, SR, subtype="PCM_16")
    path.with_suffix(".json").write_text(json.dumps({"peak": peak / 0.99, "trim_s": TRIM_S}))


def load_render(path):
    """A saved render at its level, with the first 0.25 s zeroed (the isolate fade-in)."""
    import numpy as np
    import soundfile as sf

    y, _ = sf.read(str(path), dtype="float64")
    y = y.mean(1) if y.ndim == 2 else y
    y = y * json.loads(path.with_suffix(".json").read_text())["peak"]
    y[:int(TRIM_S * SR)] = 0
    return y


def frame_split(fake, y, onset_from, frame=480, n=1024):
    """D0's error split (a proxy: the judge doesn't expose per-frame error): per 10-ms frame,
    the mean |dB| difference of the render (latency removed) from the fake, 80 Hz–8 kHz;
    classes from the fake: quiet (≥ 20 dB under its loudest frame), attack (≤ 50 ms after an
    onset of `onset_from`), sustain (the rest)."""
    import numpy as np

    def spec(x):
        x = np.asarray(x, np.float64)
        if x.ndim == 2:                                     # renders are stereo: fold to mono
            x = x.mean(axis=1)
        k = (len(x) - n) // frame + 1
        idx = np.arange(n)[None] + frame * np.arange(k)[:, None]
        return np.abs(np.fft.rfft(x[idx] * np.hanning(n), axis=1)) ** 2

    f = np.fft.rfftfreq(n, 1 / SR)
    band = (f >= 80) & (f < 8000)
    yy = np.asarray(y, np.float64)
    yy = (yy.mean(axis=1) if yy.ndim == 2 else yy)[LATENCY:]
    m = min(len(fake), len(yy))
    F, Y = spec(fake[:m]), spec(yy[:m])
    err = np.abs(10 * np.log10(Y[:, band] + 1e-12) - 10 * np.log10(F[:, band] + 1e-12)).mean(1)
    lv = 10 * np.log10(F.sum(1) + 1e-20)
    quiet = lv < lv.max() - 20
    O = np.log10(spec(np.asarray(onset_from, np.float64)[:m])[:, band] + 1e-12)
    flux = np.r_[0, np.maximum(np.diff(O, axis=0), 0).sum(1)]
    thr = flux.mean() + 1.5 * flux.std()
    onsets = [i for i in range(1, len(flux) - 1) if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]]
    attack = np.zeros(len(flux), bool)
    for i in onsets:
        attack[i:i + 6] = True
    attack &= ~quiet
    sustain = ~quiet & ~attack
    cls = {"attack": attack, "sustain": sustain, "quiet": quiet}
    return {c: (float(err[v].mean()) if v.any() else None) for c, v in cls.items()} | {
        f"{c}_frames": int(v.sum()) for c, v in cls.items()}


def _scores(fake, y, masks):
    from learn import rank_margin as RM

    out = {}
    for mname, mask in masks.items():
        out[mname] = {w: RM.distance(fake, y, mask, 0, w)[0] for w in RM.WINDOWS}
    return out


def _margins(sc_s, sc_t):
    from learn import rank_margin as RM

    return {mk: {w: RM.margin(sc_s[mk][w], sc_t[mk][w]) for w in sc_s[mk]} for mk in sc_s}


def _cell_setup(rr, menu, ps, slug, amp):
    from learn import knob_ceiling as K

    part = ps[slug]
    sel, S = menu[amp][K.START[part["gain_class"]][amp]]
    tag = _tag(slug, amp)
    T = {tuple(k.rsplit("/", 1)): v for k, v in json.loads((control_dir() / f"{tag}-target.json").read_text()).items()}
    return part, sel, S, T


def d0():
    """0b, D0: S and T through C′'s stored rebuild and through the measure DI on the 12 cells (48
    renders, saved), scored at lag 0 (masks: the DI used, and the measure DI), with the frame
    error split (MAIN)."""
    import numpy as np

    from learn import knob_ceiling as K

    ps = K.parts()
    out = root() / "step0" / "d0"
    rr = K.Renderer()
    try:
        menu = rr.menu()
        warmed = False
        for slug, amp in cells():
            tag = _tag(slug, amp)
            if (out / f"{tag}.json").exists():
                continue
            if not disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            part, sel, S, T = _cell_setup(rr, menu, ps, slug, amp)
            fake = np.load(control_dir() / f"{tag}-fake.npy")
            meas = K.measure_di(part)
            reb = np.load(control_dir() / f"{tag}-rebuilt.npy")
            n0 = rr.count
            if not warmed:
                rr.render(meas.astype(np.float32), sel, S)
                warmed = True
            res = {"cell": _key(slug, amp)}
            for dname, di, masks in (("measure", meas, {"measure": meas}), ("cprime", reb, {"v": reb, "measure": meas})):
                ys, yt = (rr.render(di.astype(np.float32), sel, x) for x in (S, T))
                save_render(out / tag / f"{dname}-S.flac", ys)
                save_render(out / tag / f"{dname}-T.flac", yt)
                sc = {"S": _scores(fake, ys, masks), "T": _scores(fake, yt, masks)}
                res[dname] = {**sc, "m": _margins(sc["S"], sc["T"]),
                              "split": {"S": frame_split(fake, ys, meas), "T": frame_split(fake, yt, meas)}}
            res["renders"] = rr.count - n0
            _atomic(out / f"{tag}.json", res)
            print(tag, {d: res[d]["m"]["measure"]["full"] for d in ("measure", "cprime")}, flush=True)
    finally:
        rr.close()


def idem_rebuild():
    """0b: x̂₂ = C′(r₁), r₁ = D0's T render through C′'s rebuild (trimmed), advanced by the render
    latency, re-equalised to fold 2, −22.9 LUFS; with crest and envelope against x̂ (TORCH)."""
    import numpy as np
    import torch

    from learn import direc as D
    from learn import knob_ceiling as K
    from learn import rank_margin as RM
    from learn import song_settings as SS
    from learn.direc_check import eq_to, to_lufs

    ps, fo = K.parts(), SS.folds()
    avg = {f: np.load(MODELS / "cache" / f"average-fold{f}.npy") for f in range(4)}
    out = root() / "step0" / "idem"
    out.mkdir(parents=True, exist_ok=True)
    meta = {}
    for slug, amp in cells():
        tag = _tag(slug, amp)
        f = fo[ps[slug]["band"]]
        r1 = load_render(root() / "step0" / "d0" / tag / "cprime-T.flac")
        net = D.load_model(SS.cprime(f)).eval()
        x2 = D.rebuild(net, r1.astype(np.float32), device=torch.device("cpu")).astype(np.float64)
        # C′ already removes the plugin's latency: its rebuild lines up with the DI (no shift)
        x2 = to_lufs(eq_to(x2, avg[2] - avg[f]))
        xh = np.load(control_dir() / f"{tag}-rebuilt.npy")
        np.save(out / f"{tag}-x2.npy", x2)
        e2, e1 = RM.envelope(x2, 10), RM.envelope(xh, 10)
        meta[_key(slug, amp)] = {"gcc_lag": RM.gcc_lag(x2, _raw_di(ps[slug])), "crest_x2": RM.crest_db(x2),
                                 "crest_x1": RM.crest_db(xh), "env_corr_10ms": float(np.corrcoef(e1, e2)[0, 1])}
        print(tag, meta[_key(slug, amp)], flush=True)
    _atomic(out / "idem.json", meta)


def idem_render():
    """0b: S and T through x̂₂ (24 renders), scored as D0 (MAIN)."""
    import numpy as np

    from learn import knob_ceiling as K

    ps = K.parts()
    out = root() / "step0" / "idem"
    meta = json.loads((out / "idem.json").read_text())
    rr = K.Renderer()
    try:
        menu = rr.menu()
        for slug, amp in cells():
            tag, key = _tag(slug, amp), _key(slug, amp)
            if (out / f"{tag}.json").exists():
                continue
            if abs(meta[key]["gcc_lag"]) > LAG_TOL:
                _atomic(out / f"{tag}.json", {"cell": key, "dropped": f"lag check {meta[key]['gcc_lag']}", "renders": 0})
                continue
            part, sel, S, T = _cell_setup(rr, menu, ps, slug, amp)
            fake = np.load(control_dir() / f"{tag}-fake.npy")
            x2, meas = np.load(out / f"{tag}-x2.npy"), K.measure_di(part)
            n0 = rr.count
            ys, yt = (rr.render(x2.astype(np.float32), sel, x) for x in (S, T))
            sc = {"S": _scores(fake, ys, {"v": x2, "measure": meas}), "T": _scores(fake, yt, {"v": x2, "measure": meas})}
            _atomic(out / f"{tag}.json", {"cell": key, **sc, "m": _margins(sc["S"], sc["T"]), "renders": rr.count - n0})
            print(tag, _margins(sc["S"], sc["T"])["measure"]["full"], flush=True)
    finally:
        rr.close()


def stft_swap(mag_from, phase_from, n=1024, hop=256):
    """|STFT(mag_from)| with the phase of STFT(phase_from), resynthesised (Hann, hop 256)."""
    import numpy as np
    from scipy.signal import istft, stft

    m = min(len(mag_from), len(phase_from))
    _, _, A = stft(np.asarray(mag_from[:m], np.float64), SR, nperseg=n, noverlap=n - hop)
    _, _, B = stft(np.asarray(phase_from[:m], np.float64), SR, nperseg=n, noverlap=n - hop)
    _, y = istft(np.abs(A) * np.exp(1j * np.angle(B)), SR, nperseg=n, noverlap=n - hop)
    y = y[:m]
    return np.pad(y, (0, m - len(y))) if len(y) < m else y


def swap():
    """0b, the swap rung on the 9 informative cells: S and T through (true magnitude, C′'s phase)
    and (C′'s magnitude, true phase), lag-checked, 36 renders (MAIN)."""
    import numpy as np

    from learn import knob_ceiling as K
    from learn import rank_margin as RM
    from learn.direc_check import to_lufs

    ps = K.parts()
    stored = stored_results()
    keys = set(informative(stored))
    out = root() / "step0" / "swap"
    rr = K.Renderer()
    try:
        menu = rr.menu()
        for slug, amp in cells():
            tag, key = _tag(slug, amp), _key(slug, amp)
            if key not in keys or (out / f"{tag}.json").exists():
                continue
            part, sel, S, T = _cell_setup(rr, menu, ps, slug, amp)
            fake = np.load(control_dir() / f"{tag}-fake.npy")
            meas, reb = K.measure_di(part), np.load(control_dir() / f"{tag}-rebuilt.npy")
            raw = _raw_di(part)
            res, n0 = {"cell": key}, rr.count
            for name, v in (("true-mag", to_lufs(stft_swap(meas, reb))), ("true-phase", to_lufs(stft_swap(reb, meas)))):
                lag = RM.gcc_lag(v, raw)
                if abs(lag) > LAG_TOL:
                    res[name] = {"dropped": f"lag check {lag}"}
                    continue
                ys, yt = (rr.render(v.astype(np.float32), sel, x) for x in (S, T))
                sc = {"S": _scores(fake, ys, {"v": v, "measure": meas}), "T": _scores(fake, yt, {"v": v, "measure": meas})}
                res[name] = {**sc, "m": _margins(sc["S"], sc["T"]), "gcc_lag": lag}
            res["renders"] = rr.count - n0
            _atomic(out / f"{tag}.json", res)
            print(tag, {k: res[k].get("m", {}).get("measure", {}).get("full") for k in ("true-mag", "true-phase")}, flush=True)
    finally:
        rr.close()
    ms = {n: {} for n in ("true-mag", "true-phase")}
    for f in out.glob("*.json"):
        r = json.loads(f.read_text())
        for n in ms:
            ms[n][r["cell"]] = r.get(n, {}).get("m", {}).get("measure", {}).get("full")
    _atomic(root() / "step0" / "swap-reading.json", swap_reorders(ms["true-mag"], ms["true-phase"], sorted(keys)))


# --- step 0c ------------------------------------------------------------------------------------------

def dac_prep():
    """0c: each cell's measure DI to `dac/in/<tag>.npy` for `learn/dac_roundtrip.py` (MAIN)."""
    import numpy as np

    from learn import knob_ceiling as K

    ps = K.parts()
    d = root() / "step0" / "dac" / "in"
    d.mkdir(parents=True, exist_ok=True)
    for slug, amp in cells():
        np.save(d / f"{_tag(slug, amp)}.npy", K.measure_di(ps[slug]))


def dac_render():
    """0c: S and T through each 4- and 9-codebook round trip (48 renders), scored as D0; the fine
    metrics of every round trip and of the resample-only control against the measure DI; the
    comparator is D0's measure-DI renders, scored the same way; then the E1′ reading (MAIN)."""
    import numpy as np

    from learn import direc as D
    from learn import knob_ceiling as K
    from learn import rank_margin as RM
    from learn.direc_check import to_lufs

    ps = K.parts()
    base = root() / "step0" / "dac"
    rt = base / "out"
    rr = K.Renderer()
    try:
        menu = rr.menu()
        for slug, amp in cells():
            tag, key = _tag(slug, amp), _key(slug, amp)
            if (base / f"{tag}.json").exists():
                continue
            part, sel, S, T = _cell_setup(rr, menu, ps, slug, amp)
            fake = np.load(control_dir() / f"{tag}-fake.npy")
            meas, raw = K.measure_di(part), _raw_di(part)
            res, n0 = {"cell": key}, rr.count
            res["rs"] = {"fine": D.fine_metrics(to_lufs(np.load(rt / f"{tag}-rs.npy")), meas)}
            for q in ("q4", "q9"):
                v = to_lufs(np.load(rt / f"{tag}-{q}.npy"))
                lag = RM.gcc_lag(v, raw)
                res[q] = {"fine": D.fine_metrics(v, meas), "gcc_lag": lag}
                if abs(lag) > LAG_TOL:
                    res[q]["dropped"] = f"lag check {lag}"
                    continue
                ys, yt = (rr.render(v.astype(np.float32), sel, x) for x in (S, T))
                sc = {"S": _scores(fake, ys, {"v": v, "measure": meas}), "T": _scores(fake, yt, {"v": v, "measure": meas})}
                res[q].update({**sc, "m": _margins(sc["S"], sc["T"])})
            res["renders"] = rr.count - n0
            _atomic(base / f"{tag}.json", res)
            print(tag, {q: res[q].get("m", {}).get("measure", {}).get("full") for q in ("q4", "q9")}, flush=True)
    finally:
        rr.close()
    stored = stored_results()
    fo = cell_folds()
    keys = [k for k in informative(stored) if fo[k] == 3]
    m_q9, m_true, crest = {}, {}, {}
    for k in keys:
        tag = _tag(*k.split("|"))
        r = json.loads((base / f"{tag}.json").read_text())
        m_q9[k] = r["q9"].get("m", {}).get("measure", {}).get("full")
        crest[k] = r["q9"]["fine"]["crest_1ms_err"]
        m_true[k] = json.loads((root() / "step0" / "d0" / f"{tag}.json").read_text())["measure"]["m"]["measure"]["full"]
    shift = json.loads((rt / "shift.json").read_text()) if (rt / "shift.json").exists() else None
    _atomic(base / "reading.json", {"cells": keys, **e1_opens(m_q9, m_true, crest, keys), "shift": shift})


# --- the render tally ------------------------------------------------------------------------------------

def tally():
    """Renders on disk under the experiment's folder, by step (from each result's `renders`)."""
    out = {}
    r = root()
    for name, pattern in (("d0", "step0/d0/*.json"), ("idem", "step0/idem/*.json"), ("swap", "step0/swap/*.json"),
                          ("dac", "step0/dac/*.json"), ("control", "control/*/*-result.json")):
        n = 0
        for f in r.glob(pattern):
            try:
                n += int(json.loads(f.read_text()).get("renders", 0))
            except (ValueError, AttributeError):
                pass
        out[name] = n
    out["total"] = sum(out.values())
    return out


# --- step 0d, 0e, 1d readers -------------------------------------------------------------------------------

def weights(stage, calibration, fixed=None):
    means = json.loads((pathlib.Path(calibration).expanduser() / "calibrate.json").read_text())["means"]
    if stage == "1a":
        res = share_rule(means, {k: PROVISIONAL[k] for k in ("short", "peak", "gap")})
    else:
        fx = json.loads((root() / "weights-1a.json").read_text())["weights"] if fixed is None else fixed
        res = share_rule(means, {"phase": PROVISIONAL["phase"]}, fixed=fx)
        res["weights"] = {**fx, **res["weights"]}
    res["means"] = means
    _atomic(root() / f"weights-{stage}.json", res)
    print(json.dumps(res["weights"]), "terms:", ",".join(f"{k}={v:g}" for k, v in res["weights"].items()), flush=True)
    return res


def capacity(run, ref, head=None):
    load = lambda d: json.loads((pathlib.Path(d).expanduser() / "overfit.json").read_text())  # noqa: E731
    r, f = load(run), load(ref)
    out = {"1b": capacity_verdict(r["end"], f["end"]), "start": r["start"], "end": r["end"], "ref_end": f["end"]}
    if head:
        h = load(head)
        out["head"] = capacity_verdict(h["end"], f["end"])
    out["arm_1e_joins"] = (not out["1b"]["pass"]) and bool(head) and out["head"]["pass"]
    _atomic(root() / "step0" / "capacity.json", out)
    print(json.dumps({k: v for k, v in out.items() if k in ("1b", "head", "arm_1e_joins")}), flush=True)
    return out


def _check2(models_check, model):
    model = str(pathlib.Path(model).expanduser())
    for k, v in models_check.items():
        if str(pathlib.Path(k).expanduser()) == model:
            return v["mean_1_3k"]
    return None


def screen(fold, cprime_dir, arm_dirs, check_json):
    load = lambda d: json.loads((pathlib.Path(d).expanduser() / "eval.json").read_text())  # noqa: E731
    c = load(cprime_dir)
    chk = json.loads(pathlib.Path(check_json).expanduser().read_text())
    evals = {a: load(d) for a, d in arm_dirs.items()}
    verdicts = {a: screen_verdict(e, c, _check2(chk, net_path(a, fold))) for a, e in evals.items()}
    out = {"fold": fold, "verdicts": verdicts}
    if "1a" in evals and "1b" in evals:
        out["parent_of_1c"] = parent_of_1c(evals["1a"], evals["1b"])
    out["render"], out["needs_yes"] = render_set(verdicts, evals)
    _atomic(root() / f"screen-f{fold}.json", out)
    print(json.dumps({a: v["passes"] for a, v in verdicts.items()}), "render", out["render"], "ask", out["needs_yes"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("reads", "gate", "d0", "idem-rebuild", "idem-render", "swap", "dac-prep", "dac-render", "tally"):
        sub.add_parser(name)
    w = sub.add_parser("weights")
    w.add_argument("--stage", choices=("1a", "1b"), required=True)
    w.add_argument("--calibration", required=True, help="the `fit --calibrate` output folder")
    c = sub.add_parser("capacity")
    c.add_argument("--run", required=True)
    c.add_argument("--ref", required=True)
    c.add_argument("--head")
    s = sub.add_parser("screen")
    s.add_argument("--fold", type=int, default=3)
    s.add_argument("--cprime", required=True, help="C′'s `fit --eval-only` folder")
    s.add_argument("--arm", action="append", default=[], help="NAME=DIR of the arm's `fit --eval-only`")
    s.add_argument("--check2", default=str(HOME / "learn/direc/cprime-folds/check.json"))
    for name in ("control-rebuild", "control-search"):
        p = sub.add_parser(name)
        p.add_argument("--arm", choices=ARMS, required=True)
        p.add_argument("--folds", type=int, nargs="+", default=[3])
        p.add_argument("--shard", default="0/1")
        p.add_argument("--cap", type=int, default=RENDER_CAP, help="raise only with the user's yes")
    for name in ("step2", "fold1"):
        p = sub.add_parser(name)
        p.add_argument("--arms", nargs="+", required=True)
        p.add_argument("--z", action="store_true", help="include 1z's rendered run")
    p = sub.add_parser("step4")
    p.add_argument("--arm", choices=ARMS, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "weights":
        weights(a.stage, a.calibration)
    elif a.cmd == "capacity":
        capacity(a.run, a.ref, a.head)
    elif a.cmd == "screen":
        screen(a.fold, a.cprime, dict(x.split("=", 1) for x in a.arm), a.check2)
    elif a.cmd == "control-rebuild":
        control_rebuild(a.arm, set(a.folds))
    elif a.cmd == "control-search":
        i, n = map(int, a.shard.split("/"))
        control_search(a.arm, set(a.folds), (i, n), a.cap)
    elif a.cmd == "step2":
        readout(a.arms, {3}, a.z, "step2")
    elif a.cmd == "fold1":
        readout(a.arms, {3, 1}, a.z, "fold1")
    elif a.cmd == "step4":
        stored = stored_results()
        res = step4(stored, arm_results(a.arm))
        fo = cell_folds()
        other = [k for k in informative(stored) if fo[k] != 3]
        ar = arm_results(a.arm)
        res["non_fold3"] = run_summary(stored, other, {k: ar[k]["rebuilt_run"]["B"] for k in other})
        _atomic(root() / "step4.json", res)
        print(json.dumps(res, default=str)[:2000], flush=True)
    elif a.cmd == "tally":
        print(json.dumps(tally()), flush=True)
    else:
        {"reads": reads, "gate": gate, "d0": d0, "idem-rebuild": idem_rebuild, "idem-render": idem_render,
         "swap": swap, "dac-prep": dac_prep, "dac-render": dac_render}[a.cmd]()


if __name__ == "__main__":
    main()
