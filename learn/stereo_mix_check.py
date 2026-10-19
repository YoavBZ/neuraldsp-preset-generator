"""The stereo check and mix vs raw track on stage F (`docs/stereo-and-mix-check-plan.md`).
Development only, zero renders; estimates with 90% band-bootstrap intervals, no pass/fail bars.

    .venv/bin/python -m learn.stereo_mix_check contexts                 # R and P stereo contexts (CPU, light)
    $MSST_PY  -m learn.stereo_mix_check separate --sep mega53           # CPU, 4 threads
    $TORCH_PY -m learn.stereo_mix_check separate --sep htdemucs         # CPU, 2 threads
    .venv/bin/python -m learn.stereo_mix_check report

TORCH_PY is ~/ndsp-presets/tools/demucs-venv/bin/python, MSST_PY ~/ndsp-presets/tools/msst-venv/bin/python.
Outputs go to ~/ndsp-presets/learn/stereo-mix-check/.

Contexts: R ("as recorded") keeps stereo tracks native and centres mono tracks at gain 1 per side,
so its (L+R)/2 is the stored mono context; P ("panned") puts the target at pan −0.6 and the other
mono guitar tracks alternately at ±0.6 (starting opposite), gL = √2·cos θ, gR = √2·sin θ,
θ = (p+1)·π/4. Runs per separator: R stereo, P stereo, P mono (R mono is the stored stem).

The pure parts (pan law, the panning rule, the channel modes, the weights, the measures, the band
bootstrap) are unit-tested (`tests/test_stereo_mix_check.py`); the commands are not.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
OUT = HOME / "learn/stereo-mix-check"
SR = 48000
CROP = 480_000
TARGET_PAN = -0.6
OTHER_PAN = 0.6
GUITAR = re.compile(r"gtr|guitar", re.I)
SEED = 20261019
N_BOOT = 4000
LEAK_PARTS = ("cambridge-Signs-ElecGtr3", "cambridge-get-out-of-bed-elecgtr2")
MODES = ("mono", "left", "right", "mid", "side", "oracle_pan", "blind_pan", "blind_pick")
RUNS = ("R_stereo", "P_stereo", "P_mono")
LSD_LO, LSD_HI = 80.0, 12000.0
FIR_TAPS = 2048


def _save(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    tmp.replace(path)


def _load(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.exists() else None


# --- pure parts ------------------------------------------------------------------------------------

def pan_gains(p):
    """(gL, gR) for pan p in [-1, 1]: √2-scaled sine/cosine law, centre = (1, 1)."""
    th = (p + 1) * math.pi / 4
    return math.sqrt(2) * math.cos(th), math.sqrt(2) * math.sin(th)


def pan_plan(tracks, target, stereo=()):
    """{track: pan} for scenario P: the target at TARGET_PAN, the other mono guitar tracks (by name)
    alternately at +OTHER_PAN, −OTHER_PAN in sorted order, every other track (and every stereo
    track in `stereo`) None (as recorded)."""
    plan, k = {}, 0
    for t in sorted(tracks):
        if t == target:
            plan[t] = TARGET_PAN
        elif t not in stereo and GUITAR.search(pathlib.Path(t).name):
            plan[t] = OTHER_PAN if k % 2 == 0 else -OTHER_PAN
            k += 1
        else:
            plan[t] = None
    return plan


GAINS = {"R": (1.0, 1.0), "P": pan_gains(TARGET_PAN)}    # the target's known channel gains (the oracle)


def place(x, pan):
    """A track (frames, channels) as stereo (2, frames): stereo native; mono centred at 1 per side
    when pan is None, else through `pan_gains`. More than two channels: their mean, centred."""
    import numpy as np

    x = np.asarray(x, np.float64)
    if x.ndim == 1:
        x = x[:, None]
    if x.shape[1] == 2 and pan is None:
        return x.T.copy()
    m = x.mean(1)
    gl, gr = (1.0, 1.0) if pan is None else pan_gains(pan)
    return np.stack([gl * m, gr * m])


def snr_db(stem, ref):
    """Gain-fitted SNR (`local_objective_1c.snr_db`)."""
    import numpy as np

    s, r = np.asarray(stem, np.float64), np.asarray(ref, np.float64)
    a = np.dot(s, r) / (np.dot(s, s) + 1e-20)
    return float(10 * np.log10(np.sum(r ** 2) / (np.sum((r - a * s) ** 2) + 1e-20)))


def oracle_weights(mix2, ref):
    """(gL, gR): the true track's LS gain in each mix channel, floored at 0 (the target's pan)."""
    import numpy as np

    r = np.asarray(ref, np.float64)
    g = [max(0.0, float(np.dot(np.asarray(c, np.float64), r) / (np.dot(r, r) + 1e-20))) for c in mix2]
    return tuple(g)


def blind_weights(stem2):
    """(wL, wR): the stereo stem's own channel RMS (what the product could estimate)."""
    import numpy as np

    return tuple(float(np.sqrt(np.mean(np.asarray(c, np.float64) ** 2))) for c in stem2)


def modes(stem2, mono_stem, target_gains):
    """{mode: 1-D signal} from a stereo stem (2, n), the mono-input stem and the target's known
    channel gains (the ORACLE pan: (1, 1) as recorded, `pan_gains(TARGET_PAN)` panned)."""
    import numpy as np

    L, R = np.asarray(stem2[0], np.float64), np.asarray(stem2[1], np.float64)
    go = target_gains
    gb = blind_weights(stem2)
    return {"mono": np.asarray(mono_stem, np.float64), "left": L, "right": R, "mid": (L + R) / 2,
            "side": (L - R) / 2, "oracle_pan": go[0] * L + go[1] * R, "blind_pan": gb[0] * L + gb[1] * R,
            "blind_pick": L if gb[0] >= gb[1] else R}                 # post hoc (results doc): the louder stem channel


def pan_of(gl, gr):
    """The pan p whose gains have the ratio gl:gr (inverse of `pan_gains`); None if both are 0."""
    if gl <= 0 and gr <= 0:
        return None
    return 4 * math.atan2(gr, gl) / math.pi - 1


def band_boot(pairs, n=N_BOOT, seed=SEED):
    """Band-weighted mean of (band, value) pairs and its 90% band bootstrap (`generate_routing`)."""
    import random
    import statistics as st

    groups = {}
    for band, v in pairs:
        groups.setdefault(band, []).append(v)
    bands = sorted(groups)
    mean = st.mean(st.mean(groups[b]) for b in bands)
    rng = random.Random(seed)
    draws = sorted(st.mean(st.mean(groups[b]) for b in (rng.choice(bands) for _ in bands)) for _ in range(n))
    return {"band_mean": round(mean, 3), "lo": round(draws[int(0.05 * n)], 3), "hi": round(draws[int(0.95 * n)], 3),
            "part_mean": round(st.mean(v for _, v in pairs), 3), "n": len(pairs), "bands": len(bands)}


def third_octave_db(x, lo=LSD_LO, hi=LSD_HI, sr=SR):
    """Long-term 1/3-octave band levels (dB) of x, Welch 8192."""
    import numpy as np
    from scipy.signal import welch

    f, p = welch(np.asarray(x, np.float64), sr, nperseg=8192)
    centres = [1000 * 2 ** (k / 3) for k in range(-30, 30)]
    out = []
    for c in centres:
        a, b = c / 2 ** (1 / 6), c * 2 ** (1 / 6)
        if a < lo or b > hi:
            continue
        out.append(10 * np.log10(np.sum(p[(f >= a) & (f < b)]) + 1e-20))
    return np.asarray(out)


def lsd_db(x, ref):
    """RMS dB difference of the 1/3-octave long-term spectra after one broadband gain."""
    import numpy as np

    d = third_octave_db(x) - third_octave_db(ref)
    return float(np.sqrt(np.mean((d - d.mean()) ** 2)))


def active_frames(ref, frame=4800, floor_db=25.0):
    import numpy as np

    n = len(ref) // frame
    r = np.asarray(ref[:n * frame], np.float64).reshape(n, frame)
    rms = np.sqrt(np.mean(r ** 2, 1)) + 1e-20
    return 20 * np.log10(rms) >= 20 * np.log10(rms.max()) - floor_db


def crest_db(x, mask, frame=4800):
    """Median over the masked 100-ms frames of 20·log10(peak / RMS)."""
    import numpy as np

    n = len(mask)
    f = np.asarray(x[:n * frame], np.float64).reshape(n, frame)[mask]
    return float(np.median(20 * np.log10((np.abs(f).max(1) + 1e-20) / (np.sqrt(np.mean(f ** 2, 1)) + 1e-20))))


def hf_ratio_db(x, sr=SR):
    """Energy 3–10 kHz over 0.2–3 kHz (dB): a brightness measure (distortion fizz lives up there,
    but so does separator high-frequency loss; it does not tell them apart)."""
    import numpy as np
    from scipy.signal import welch

    f, p = welch(np.asarray(x, np.float64), sr, nperseg=8192)
    return float(10 * np.log10((p[(f >= 3000) & (f < 10000)].sum() + 1e-20) / (p[(f >= 200) & (f < 3000)].sum() + 1e-20)))


def ls_fir_heldout(x, y, taps=FIR_TAPS):
    """The LS FIR recovery of y from x, fitted on one half and applied to the other, both ways
    (no fitting on the scored audio)."""
    import numpy as np

    h = len(x) // 2
    wa, wb = ls_weights(x[:h], y[:h], taps), ls_weights(x[h:], y[h:], taps)
    return np.concatenate([apply_fir(x, wb, taps)[:h], apply_fir(x, wa, taps)[h:]])


def apply_fir(x, w, taps=FIR_TAPS):
    import numpy as np
    from scipy.signal import fftconvolve

    h = taps // 2
    return fftconvolve(np.asarray(x, np.float64), w)[h:h + len(x)]


def ls_weights(x, y, taps=FIR_TAPS):
    """The least-squares FIR (taps, centred: half non-causal) from x onto y."""
    import numpy as np
    from scipy.linalg import solve_toeplitz

    x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
    n, h = len(x), taps // 2
    nfft = 1 << int(math.ceil(math.log2(2 * n)))
    X, Y = np.fft.rfft(x, nfft), np.fft.rfft(y, nfft)
    rxx = np.fft.irfft(X * np.conj(X), nfft)[:taps]
    rxy = np.fft.irfft(Y * np.conj(X), nfft)                 # rxy[k] = sum y[t+k] x[t]
    p = np.concatenate([rxy[-h:], rxy[:taps - h]])           # lags −h … taps−h−1
    return solve_toeplitz(rxx + 1e-9 * rxx[0] * (np.arange(taps) == 0), p)


# --- commands --------------------------------------------------------------------------------------

def parts():
    from learn import arm_a_mega53 as A

    return [(s, A.pool_band(s)) for s in A.pool_slugs()]


def _session(slug):
    """(part, record, session folder) for a stage F part."""
    from learn import arm_a_mega53 as A
    from learn import separate as SEP

    part = A.f_part(slug)
    rec = json.loads((part["crop"] / "record.json").read_text())
    cat = json.loads((PLUGIN_ROOT / "docs/validation-datasets.json").read_text()) if part["set"] == 12 \
        else A.shim_catalog(rec)
    s = [x for x in cat["sessions"] if x["source"] == rec["source"] and x["song"] == rec["song"]]
    assert len(s) == 1, slug
    return part, rec, SEP.DATA / s[0]["path"]


def target_track(rec, part):
    """The part's reference amp track inside the record's mix tracks."""
    pr = rec.get("pairing", {}).get("reference")
    if pr:
        return pr
    import json as _j

    cat = _j.loads((PLUGIN_ROOT / "docs/validation-datasets.json").read_text())
    s = [x for x in cat["sessions"] if x["source"] == rec["source"] and x["song"] == rec["song"]][0]
    p = [q for q in s["parts"] if q["part"] == rec["part"]][0]
    return p["reference"]


def cmd_contexts():
    import numpy as np

    from analysis import io
    from learn import arm_a_mega53 as A
    from learn import separate as SEP

    d = OUT / "contexts"
    d.mkdir(parents=True, exist_ok=True)
    clog = json.loads(A.fdir("contexts", "log.json").read_text())
    log = _load(d / "log.json") or {}
    for slug, band in parts():
        if slug in log and (d / f"{slug}-P.npy").exists():
            continue
        part, rec, root = _session(slug)
        n, a, b = rec["session_frames"], rec["excerpt_start_frame"], rec["excerpt_end_frame"]
        cs, ce = SEP.window(n, a, b, SEP.PAD_S * SR)
        tgt = target_track(rec, part)
        assert tgt in rec["included_mix_tracks"], (slug, tgt)
        import soundfile as sf

        stereo = {nm for nm in rec["included_mix_tracks"] if sf.info(str(root / nm)).channels >= 2}
        assert tgt not in stereo, (slug, tgt)
        plan = pan_plan(rec["included_mix_tracks"], tgt, stereo)
        R, P = np.zeros((2, ce - cs)), np.zeros((2, ce - cs))
        chans = {}
        for name in rec["included_mix_tracks"]:
            au = io.load(root / name)
            assert au.sha256 == rec["verified_source_sha256"][name], (slug, name)
            s = np.asarray(au.samples, np.float64)[:n]
            x = np.zeros((n, s.shape[1]))
            x[:len(s)] = s
            x = x[cs:ce]
            chans[name] = s.shape[1]
            R += place(x, None)
            P += place(x, plan[name])
        stored = np.load(A.fdir("contexts", f"{slug}.npy")).astype(np.float64)
        dev = float(np.max(np.abs((R[0] + R[1]) / 2 - stored)))
        assert dev < 1e-5, (slug, dev)
        assert clog[slug]["offset"] == a - cs, slug
        np.save(d / f"{slug}-R.npy", R.astype(np.float32))
        np.save(d / f"{slug}-P.npy", P.astype(np.float32))
        log[slug] = {"band": band, "offset": a - cs, "target": tgt, "target_channels": chans[tgt],
                     "mid_vs_stored_max_abs": dev,
                     "panned": {k: v for k, v in plan.items() if v is not None},
                     "stereo_tracks": sorted(k for k, c in chans.items() if c == 2),
                     "other_guitars_stereo": sorted(k for k, c in chans.items()
                                                    if c == 2 and GUITAR.search(pathlib.Path(k).name))}
        _save(d / "log.json", log)
        print(slug, {k: v for k, v in log[slug].items() if k != "panned"}, flush=True)
    print(f"contexts: {len(log)} parts")


class StereoSep:
    """Stereo in, stereo out, with the stored mono path's model and settings."""

    def __init__(self, sep):
        from learn import separate as SEP

        self.name = sep
        self.mono = SEP.guitar_separator(sep)

    def stereo(self, x2):
        import numpy as np

        x2 = np.asarray(x2, np.float32)
        n = x2.shape[1]
        if self.name == "mega53":
            from learn import separator_screen as SCR
            from utils.model_utils import demix

            m = self.mono
            y = np.stack([SCR.to44(c.astype(np.float64)) for c in x2]).astype(np.float32)
            out = demix(m.config, m.model, y, m.device, "bs_roformer", pbar=False)[SCR.STEM]
            s = SCR.swap_used_mb()
            if m.swap0 is not None and s is not None and s - m.swap0 > SCR.SWAP_GROWTH_MB:
                raise SystemExit(f"swap grew by {s - m.swap0:.0f} MB: stopping Mega-53")
            return np.stack([SCR.to48(out[c], n) for c in range(2)])
        import julius
        import torch

        sep = self.mono.sep
        _, stems = sep.separate_tensor(torch.from_numpy(np.ascontiguousarray(x2)), SR)
        g = julius.resample_frac(stems["guitar"], sep.samplerate, SR).numpy()
        out = np.zeros((2, n), np.float32)
        k = min(n, g.shape[1])
        out[:, :k] = g[:, :k]
        return out


def cmd_separate(sep):
    import numpy as np

    d = OUT / "sep" / sep
    d.mkdir(parents=True, exist_ok=True)
    clog = _load(OUT / "contexts" / "log.json")
    log = _load(d / "log.json") or {}
    todo = [(s, r) for s, _ in parts() for r in RUNS if not (d / f"{s}-{r}.npy").exists()]
    if not todo:
        print("SEPARATE DONE", sep)
        return
    model = StereoSep(sep)
    if sep == "htdemucs":
        import torch

        torch.set_num_threads(2)
    if not (d / "identity.json").exists():           # dual-mono through the stereo path = the stored stem
        from learn import arm_a_mega53 as A

        slug = parts()[0][0]
        m = np.load(A.fdir("contexts", f"{slug}.npy")).astype(np.float32)
        off = clog[slug]["offset"]
        y = model.stereo(np.stack([m, m])).mean(0)[off:off + CROP]
        dev = float(np.max(np.abs(y - np.load(A.sep_crop(sep, slug)))))
        _save(d / "identity.json", {"part": slug, "max_abs_diff": dev, "ok": dev < 1e-4})
        print(sep, "identity", slug, dev, flush=True)
        if dev >= 1e-4:
            raise SystemExit(f"{sep}: the stereo path does not reproduce the stored stem ({dev})")
    for slug, run in todo:
        sc, kind = run.split("_")
        x2 = np.load(OUT / "contexts" / f"{slug}-{sc}.npy")
        off = clog[slug]["offset"]
        t = time.time()
        if kind == "mono":
            y = np.asarray(model.mono(x2.mean(0)), np.float32)[off:off + CROP]
        else:
            y = model.stereo(x2)[:, off:off + CROP]
        assert y.shape[-1] == CROP, (slug, run, y.shape)
        np.save(d / f"{slug}-{run}.npy", y.astype(np.float32))
        log[f"{slug}|{run}"] = {"wall_s": round(time.time() - t, 1)}
        _save(d / "log.json", log)
        print(sep, slug, run, log[f"{slug}|{run}"], flush=True)
    print("SEPARATE DONE", sep)


def cmd_report():
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import confirm_run as CR

    clog = _load(OUT / "contexts" / "log.json")
    rows = {}
    for slug, band in parts():
        part = A.f_part(slug)
        ref = CR.mono(part["crop"] / "reference.wav")
        off = clog[slug]["offset"]
        row = {"band": band, "leak_flag": slug in LEAK_PARTS, "stereo": {}, "input_snr": {}}
        mixes = {sc: np.load(OUT / "contexts" / f"{slug}-{sc}.npy").astype(np.float64)[:, off:off + CROP]
                 for sc in "RP"}
        for sc, m2 in mixes.items():
            mono_in = m2.mean(0)
            row["input_snr"][sc] = {k: snr_db(v, ref) for k, v in modes(m2, mono_in, GAINS[sc]).items()}
            row.setdefault("ls_pan_estimate", {})[sc] = pan_of(*oracle_weights(m2, ref))   # diagnostic
        for sep in ("mega53", "htdemucs"):
            sd = OUT / "sep" / sep
            if not all((sd / f"{slug}-{r}.npy").exists() for r in RUNS):
                continue
            stored = np.load(A.sep_crop(sep, slug)).astype(np.float64)
            stored_snr = json.loads(A.fdir("sep", sep, "log.json").read_text())[slug]["snr_db_vs_reference"]
            res = {"stored_snr_check": abs(snr_db(stored, ref) - stored_snr)}
            for sc in "RP":
                st2 = np.load(sd / f"{slug}-{sc}_stereo.npy").astype(np.float64)
                mono_stem = stored if sc == "R" else np.load(sd / f"{slug}-P_mono.npy").astype(np.float64)
                sn = {k: snr_db(v, ref) for k, v in modes(st2, mono_stem, GAINS[sc]).items()}
                res[sc] = {"snr": sn, "gain_vs_mono": {k: v - sn["mono"] for k, v in sn.items() if k != "mono"},
                           "blind_pan": pan_of(*blind_weights(st2))}
            row["stereo"][sep] = res
        # task 3: mix vs raw
        crop = part["crop"]
        mixc, backing = CR.mono(crop / "mix.wav"), CR.mono(crop / "backing.wav")
        row["mix_minus_backing_vs_ref_max_abs"] = float(np.max(np.abs(mixc - backing - ref)))
        mask = active_frames(ref)
        est = {"ls_from_mix_oracle": ls_fir_heldout(mixc, ref)}
        for sep in ("mega53", "htdemucs"):
            est[sep] = np.load(A.sep_crop(sep, slug)).astype(np.float64)
        ref_crest, ref_hf = crest_db(ref, mask), hf_ratio_db(ref)
        row["raw"] = {"crest_db": ref_crest, "hf_ratio_db": ref_hf}
        row["vs_raw"] = {k: {"lsd_db": lsd_db(v, ref), "crest_diff_db": crest_db(v, mask) - ref_crest,
                             "bright_diff_db": hf_ratio_db(v) - ref_hf, "snr_db": snr_db(v, ref)} for k, v in est.items()}
        rows[slug] = row
        print(slug, "done", flush=True)
    rep = {"rows": rows, "summary": summarise(rows), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(OUT / "report.json", rep)
    print(json.dumps(rep["summary"], indent=1))


def summarise(rows):
    s = {"stereo": {}, "input_snr": {}, "vs_raw": {}}
    for sc in "RP":
        s["input_snr"][sc] = {m: band_boot([(r["band"], r["input_snr"][sc][m] - r["input_snr"][sc]["mono"])
                                            for r in rows.values()]) for m in MODES if m != "mono"}
        for sep in ("mega53", "htdemucs"):
            rs = [r for r in rows.values() if sep in r["stereo"]]
            if not rs:
                continue
            s["stereo"].setdefault(sep, {})[sc] = {
                "mono_snr": band_boot([(r["band"], r["stereo"][sep][sc]["snr"]["mono"]) for r in rs]),
                **{m: band_boot([(r["band"], r["stereo"][sep][sc]["gain_vs_mono"][m]) for r in rs])
                   for m in MODES if m != "mono"}}
    for k in ("ls_from_mix_oracle", "mega53", "htdemucs"):
        vs = [(r["band"], r["vs_raw"][k]) for r in rows.values()]
        s["vs_raw"][k] = {
            **{m: band_boot([(b, v[m]) for b, v in vs]) for m in ("lsd_db", "crest_diff_db", "bright_diff_db")},
            "share_lsd_over_3db": round(sum(v["lsd_db"] > 3 for _, v in vs) / len(vs), 3),
            "share_crest_loss_over_1db": round(sum(v["crest_diff_db"] < -1 for _, v in vs) / len(vs), 3),
            "share_bright_loss_over_1db": round(sum(v["bright_diff_db"] < -1 for _, v in vs) / len(vs), 3)}
    s["mix_minus_backing_vs_ref_max_abs"] = max(r["mix_minus_backing_vs_ref_max_abs"] for r in rows.values())
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("contexts", "separate", "report"))
    ap.add_argument("--sep", choices=("mega53", "htdemucs"))
    a = ap.parse_args(argv)
    if a.cmd == "separate":
        if a.sep is None:
            from learn import separate as SEP

            a.sep = SEP.DEFAULT_SEPARATOR
        cmd_separate(a.sep)
    else:
        {"contexts": cmd_contexts, "report": cmd_report}[a.cmd]()


if __name__ == "__main__":
    main()
