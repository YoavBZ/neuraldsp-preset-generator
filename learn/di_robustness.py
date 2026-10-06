"""Does the judge still choose well through a wrong DI? (`docs/di-robustness-plan.md`)

    .venv/bin/python -m learn.di_robustness render --out ~/ndsp-presets/learn/di-robust
    .venv/bin/python -m learn.di_robustness score --out ~/ndsp-presets/learn/di-robust
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

KILL = pathlib.Path(os.path.expanduser("~/ndsp-presets/runs/kill"))
CROPS = pathlib.Path(os.path.expanduser("~/ndsp-presets/references/validation-crops"))
SR, LATENCY = 48000, 52
BAND_SETS = ("recording", "union")
VARIANTS = ("swap", "mild", "swap+mild")
# Training-free rebuilt DIs (plan amendment): the recording itself, equalised to a
# typical DI's spectrum at the assumed level; judged with lag 0.
REBUILT = ("flatref", "flatstem")
REPORTED = ("avg",)
STEMS = pathlib.Path(os.path.expanduser("~/ndsp-presets/learn/poc/stems"))
ASSUMED_LUFS = -22.9
HALF_A, HALF_B = (1.0, 5.5), (5.5, 10.0)
SEED = 20261006


def mono(path):
    import soundfile as sf

    x, sr = sf.read(str(path), dtype="float64", always_2d=True)
    assert sr == SR
    return x.mean(axis=1)


def k1_parts():
    j = json.loads((KILL / "k-judge-pr12-clean.json").read_text())
    rows = {r["part"]: r for r in j["k1"]["recording"]["rows"]}
    lags = {p: j["lags"][p]["lag"] for p in rows}
    return sorted(rows), {p: rows[p]["band"] for p in rows}, lags, j


# --- degradations -------------------------------------------------------------

N_FFT = 4096


def smoothed_spectrum(x):
    """Long-term magnitude spectrum (dB) on N_FFT bins, smoothed over 1/6 octave."""
    import numpy as np

    hop = N_FFT // 4
    frames = np.lib.stride_tricks.sliding_window_view(x, N_FFT)[::hop] * np.hanning(N_FFT)
    p = (np.abs(np.fft.rfft(frames, axis=1)) ** 2)
    e = p.sum(1)
    p = p[10 * np.log10(e + 1e-20) >= 10 * np.log10(e.max() + 1e-20) - 40].mean(0)
    f = np.fft.rfftfreq(N_FFT, 1 / SR)
    out = np.empty_like(p)
    for i, fc in enumerate(f):
        lo, hi = fc * 2 ** (-1 / 12), fc * 2 ** (1 / 12)
        m = (f >= lo) & (f <= hi)
        out[i] = p[m].mean() if m.any() else p[i]
    return 10 * np.log10(out + 1e-20)


def apply_gain_db(x, gain_db):
    """Zero-phase FIR filter with the given per-bin gain (N_FFT // 2 + 1 bins)."""
    import numpy as np

    h = np.fft.irfft(10 ** (np.clip(gain_db, -15, 15) / 20), N_FFT)
    h = np.roll(h, N_FFT // 2) * np.hanning(N_FFT)
    y = np.convolve(x, h, mode="full")[N_FFT // 2: N_FFT // 2 + len(x)]
    return y


def rms(x):
    import numpy as np

    return float(np.sqrt(np.mean(x ** 2)) + 1e-12)


def degrade(variant, part, di, others, rng):
    """The degraded DI for one part: `others` maps band -> list of DI arrays."""
    import numpy as np

    y = di.copy()
    if "swap" in variant:
        band = rng.choice(sorted(others))
        target = np.mean([smoothed_spectrum(o) for o in others[band]], axis=0)
        own = smoothed_spectrum(y)
        gain = (target - target.mean()) - (own - own.mean())
        y = apply_gain_db(y, gain)
    if "mild" in variant:
        f = np.fft.rfftfreq(N_FFT, 1 / SR)
        sign = rng.choice((-1, 1))
        tilt = sign * 3.0 * np.clip((np.log10(np.maximum(f, 1)) - 3.0), -1, 1)
        y = apply_gain_db(y, tilt)
        t = np.arange(int(0.05 * SR)) / SR
        h = np.exp(-t / 0.010)
        h /= h.sum()
        y = 0.5 * y + 0.5 * np.convolve(y, h)[:len(y)]
        peak = np.abs(y).max()
        y = 0.9 * peak * np.tanh(y / (0.9 * peak))
        band = rng.choice(sorted(others))
        bleed = others[band][rng.randrange(len(others[band]))]
        n = min(len(bleed), len(y))
        y[:n] += bleed[:n] / rms(bleed[:n]) * rms(y) * 10 ** (-20 / 20)
    return y * (rms(di) / rms(y))


def average_balance(di, others):
    """The true DI, equalised to the average spectrum of the other folds' DIs."""
    import numpy as np

    target = np.mean([smoothed_spectrum(o) for b in others for o in others[b]], axis=0)
    own = smoothed_spectrum(di)
    y = apply_gain_db(di, (target - target.mean()) - (own - own.mean()))
    return y * (rms(di) / rms(y))


def stem_usable():
    m = json.loads((STEMS / "manifest.json").read_text())
    return {p for p, v in m["parts"].items() if v.get("usable")}


def recording_for(part, variant):
    """What the judge compares against on half A: the stem for flatstem, else the amp track."""
    if variant == "flatstem":
        return mono(STEMS / "htdemucs_6s" / part / "instrumental_guitar.wav")
    return mono(CROPS / part / "reference.wav")


def rebuilt(variant, part, others):
    """The recording, equalised to the average DI spectrum of `others`, at −22.9 LUFS."""
    import numpy as np
    import pyloudnorm

    x = recording_for(part, variant)
    target = np.mean([smoothed_spectrum(o) for b in others for o in others[b]], axis=0)
    own = smoothed_spectrum(x)
    y = apply_gain_db(x, (target - target.mean()) - (own - own.mean()))
    lufs = pyloudnorm.Meter(SR).integrated_loudness(y)
    return y * 10 ** ((ASSUMED_LUFS - lufs) / 20)


# --- renders ----------------------------------------------------------------------

def work(job):
    import numpy as np
    import soundfile as sf

    import render_preset_panel as RP
    from match.renderer_au import AudioUnitRenderer
    from packs.loader import load_pack

    out, parts = job
    pack = load_pack("morgan")

    class PanelRenderer(AudioUnitRenderer):
        commands: dict = {}

        def _state_command(self, settings):
            select, edits = self.commands[settings["panel"]]
            command = {"edits": edits}
            if select is not None:
                command["selectAmp"] = select
            return command

    renderer = PanelRenderer("morgan", process_policy="reuse")
    panel = json.loads((KILL / "pr12-clean" / "index.json").read_text())
    names = sorted({r["candidate"] for r in panel["rows"] if "file" in r and r["candidate"] != "template"})
    args = argparse.Namespace(amp="pr12", factory_dir=RP.FACTORY)
    menu = RP.candidates(args, pack, renderer)
    PanelRenderer.commands = {n: RP.preset_edits(menu[n][0], pack, renderer, "pr12", menu[n][1])
                              for n in names}
    done = 0
    try:
        for part, variant in parts:
            di = np.load(out / "di" / f"{part}--{variant}.npy").astype(np.float32)
            renderer.render(di, {"panel": "template+R"})                 # warm-up, discarded
            d = out / "renders" / variant / part
            d.mkdir(parents=True, exist_ok=True)
            for n in names:
                path = d / f"{RP._slug(n)}.wav"
                if not path.exists():
                    sf.write(path, np.asarray(renderer.render(di, {"panel": n}).audio), SR,
                             subtype="FLOAT")
                    done += 1
    finally:
        renderer.close()
    return done


def render(out):
    import numpy as np

    from learn import train as TR

    parts, band, lags, _ = k1_parts()
    fold_of, band_of = TR.k3_folds()
    dis = {p: mono(CROPS / p / "di.wav") for p in band_of}
    (out / "di").mkdir(parents=True, exist_ok=True)
    usable = stem_usable()
    jobs = []
    for p in parts:
        others = {}
        for q, b in band_of.items():
            if fold_of[b] != fold_of[band[p]]:
                others.setdefault(b, []).append(dis[q])
        for v in VARIANTS:
            path = out / "di" / f"{p}--{v}.npy"
            if not path.exists():
                np.save(path, degrade(v, p, dis[p], others, random.Random(f"{SEED}-{p}-{v}")))
            jobs.append((p, v))
        for v in REPORTED:
            path = out / "di" / f"{p}--{v}.npy"
            if not path.exists():
                np.save(path, average_balance(dis[p], others))
            jobs.append((p, v))
        for v in REBUILT:
            if v == "flatstem" and p not in usable:
                continue
            path = out / "di" / f"{p}--{v}.npy"
            if not path.exists():
                np.save(path, rebuilt(v, p, others))
            jobs.append((p, v))
    workers = 3
    chunks = [(out, jobs[i::workers]) for i in range(workers)]
    with ProcessPoolExecutor(workers) as pool:
        print(f"rendered {sum(pool.map(work, chunks))}")


# --- scoring --------------------------------------------------------------------

def score_part(job):
    import numpy as np

    import render_preset_panel as RP
    from analysis.aligned import aligned_distance

    out, p, lag, names, files = job
    ref, di = mono(CROPS / p / "reference.wav"), mono(CROPS / p / "di.wav")
    res = {"true_B": {}, "pick": {}}
    for bs in BAND_SETS:
        res["true_B"][bs] = {n: aligned_distance(ref, mono(files[n]), di, lag=lag,
                                                 render_latency=LATENCY, start_s=HALF_B[0],
                                                 end_s=HALF_B[1], bands=bs).distance
                             for n in names}
        res["true_A"] = res.get("true_A", {})
        res["true_A"][bs] = {n: aligned_distance(ref, mono(files[n]), di, lag=lag,
                                                 render_latency=LATENCY, start_s=HALF_A[0],
                                                 end_s=HALF_A[1], bands=bs).distance
                             for n in names}
        for v in VARIANTS + REBUILT + REPORTED:
            path = out / "di" / f"{p}--{v}.npy"
            if not path.exists():
                continue
            ddi = np.load(path)
            rec = recording_for(p, v) if v in REBUILT else ref
            vlag = 0 if v in REBUILT else lag
            dA = {}
            for n in names:
                x = mono(out / "renders" / v / p / f"{RP._slug(n)}.wav")
                dA[n] = aligned_distance(rec, x, ddi, lag=vlag, render_latency=LATENCY,
                                         start_s=HALF_A[0], end_s=HALF_A[1], bands=bs).distance
            ok = {n: d for n, d in dA.items() if d is not None}
            res["pick"][f"{v}|{bs}"] = min(ok, key=ok.get) if ok else None
    print(p, flush=True)
    return p, res


def score(out):
    import kill_tests as K

    parts, band, lags, j = k1_parts()
    panel = json.loads((KILL / "pr12-clean" / "index.json").read_text())
    names = sorted({r["candidate"] for r in panel["rows"] if "file" in r and r["candidate"] != "template"})
    files = {}
    for r in panel["rows"]:
        if "file" in r:
            files.setdefault(r["part"], {})[r["candidate"]] = r["file"]
    jobs = [(out, p, lags[p], names, files[p]) for p in parts]
    with ProcessPoolExecutor(4) as pool:
        res = dict(pool.map(score_part, jobs))
    summary, rows_out = {}, {}
    for bs in BAND_SETS:
        for v in ["true"] + list(VARIANTS) + list(REBUILT) + list(REPORTED):
            rows = []
            for p in parts:
                B, A = res[p]["true_B"][bs], res[p]["true_A"][bs]
                if B.get("template+R") is None:
                    continue
                okA = {n: d for n, d in A.items() if d is not None}
                oracle = min(okA, key=okA.get)
                pick = oracle if v == "true" else res[p]["pick"].get(f"{v}|{bs}")
                if pick is None or B.get(pick) is None or B.get(oracle) is None:
                    continue
                lt = math.log(B["template+R"])
                rows.append({"part": p, "band": band[p], "pick": pick, "oracle": oracle,
                             "vs_template": math.log(B[pick]) - lt,
                             "vs_oracle": math.log(B[pick]) - math.log(B[oracle])})
            n = len(rows)
            near = sum(r["vs_oracle"] <= 0.150 for r in rows)
            by_band = {}
            for r in rows:
                by_band.setdefault(r["band"], []).append(r["vs_oracle"] <= 0.150)
            bands_near = sum(statistics.mean(v_) > 0.5 for v_ in by_band.values())
            stat = K.band_stat(rows, "vs_template")
            summary[f"{v}|{bs}"] = {
                "parts": n, "within_0.150_of_oracle": near, "bands": len(by_band),
                "bands_mostly_within": bands_near,
                "same_pick_as_oracle": sum(r["pick"] == r["oracle"] for r in rows),
                "vs_templateR": stat,
                "pass": bool(v in VARIANTS and near > n / 2 and bands_near > len(by_band) / 2
                             and stat and stat["band_median_log_ratio"] <= math.log(0.9)),
            }
            rows_out[f"{v}|{bs}"] = rows
    decision = all(summary[f"{v}|{bs}"]["pass"] for v in ("swap", "swap+mild") for bs in BAND_SETS)
    (out / "result.json").write_text(json.dumps({"summary": summary, "rows": rows_out,
                                                 "build_di_recovery": decision}, indent=1))
    for k, s in summary.items():
        st = s["vs_templateR"] or {}
        print(f"{k:22s} near {s['within_0.150_of_oracle']}/{s['parts']} bands {s['bands_mostly_within']}/{s['bands']} "
              f"same {s['same_pick_as_oracle']} | vs T+R {st.get('band_median_log_ratio')} p {st.get('sign_flip_p_two_sided')} | pass {s['pass']}")
    print("build DI recovery:", decision)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("render", "score"))
    ap.add_argument("--out", type=pathlib.Path, required=True)
    args = ap.parse_args()
    out = args.out.expanduser()
    out.mkdir(parents=True, exist_ok=True)
    (render if args.cmd == "render" else score)(out)


if __name__ == "__main__":
    main()
