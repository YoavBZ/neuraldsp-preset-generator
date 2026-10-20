"""Pan side as a separation hint: the stage F synthetic-pan screen (`docs/stereo-side-plan.md`).
Development only, zero renders; band-bootstrapped effect sizes against a declared +2 dB gate.

    $MSST_PY  -m learn.stereo_side_screen separate --sep mega53 --disk-guard-gb 26   # CPU, 4 threads
    $TORCH_PY -m learn.stereo_side_screen separate --sep htdemucs --disk-guard-gb 26 # CPU, 2 threads
    $MSST_PY  -m learn.stereo_side_screen centre --disk-guard-gb 26                  # MDX23C on Mega-53 crops
    .venv/bin/python -m learn.stereo_side_screen report
    .venv/bin/python -m learn.stereo_side_screen coherence   # amendment 1: the coherence mask, stored stems

TORCH_PY is ~/ndsp-presets/tools/demucs-venv/bin/python, MSST_PY ~/ndsp-presets/tools/msst-venv/bin/python.
Outputs go to ~/ndsp-presets/learn/stereo-side-screen/. Scenarios R and P reuse the stereo check's
contexts and stems (`learn/stereo_mix_check.py`); HP, LC and SP are rebuilt in memory from the
session tracks and only 10-s crops are stored.

The pure parts (scenario plans, instrument grouping, the pan index, the masks, the blind peak,
SI-SDR, the bootstrap with draws, Holm) are unit-tested (`tests/test_stereo_side_screen.py`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import re
import shutil
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from learn import stereo_mix_check as S  # noqa: E402

HOME = S.HOME
OUT = HOME / "learn/stereo-side-screen"
SMC = S.OUT                                    # the stereo check's outputs (R and P)
SR, CROP = S.SR, S.CROP
SEED, N_BOOT = S.SEED, S.N_BOOT
DEFAULT_DISK_GUARD_GB = 31.0
SIGMA = 0.3                                    # the ILD mask width, fixed in the plan, not swept
NFFT, HOP = 2048, 512
FLOOR = 1e-10                                  # bins below this share of the crop's peak bin energy: mask 0
HIST_BINS = 41
ACOUSTIC = re.compile(r"acoust", re.I)
INSTR_SUFFIX = re.compile(r"(mic|amp|close|di)\d*$", re.I)
# scenario: (target pan, other-guitar rule, other pan); "alt" alternates +p, -p by instrument
NEW = {"LC": (0.0, "alt", 1.0), "HP": (-1.0, "all", 1.0), "SP": (-0.6, "all", -0.6)}
TARGET_PANS = {"R": 0.0, "P": S.TARGET_PAN, **{k: v[0] for k, v in NEW.items()}}
SCENARIOS = ("R", "P", "LC", "HP", "SP")
CENTRE_SCEN = ("LC", "R")
CENTRE_CHECK_PARTS = 3                         # overlap-8 check on the first 3 LC parts
CENTRE_OVERLAP = 2
SPLITTERS = ("M", "a", "b", "c", "d", "e", "f_pick", "f_mask")
GATED = (("P", "a"), ("P", "c"), ("P", "d"), ("LC", "c"), ("LC", "d"), ("LC", "e"))
GATE_DB, LOWER_DB, STOP_DB, LSD_GUARD_DB, ALPHA = 2.0, 1.0, 0.5, 1.0, 0.05
COH_TAU, COH_K = 0.5, 10.0                     # amendment 1: the coherence mask's threshold and slope, fixed
COH_SPLITTERS = ("c", "g", "gc")
COH_GATED = (("LC", "g"), ("LC", "gc"), ("P", "gc"))
CENTRE_DIR = HOME / "tools/msst/weights-centre"
CENTRE_FILES = {"config_mdx23c_similarity.yaml": "90645b4ffb0711172bc1279233d5982f3814ecb27ec8bc0fd4e19cf8453a9c06",
                "model_mdx23c_ep_271_l1_freq_72.2383.ckpt":
                    "1227f8d97c7436004d03e46091427393abefebcc08ce53ef30082742c4e482f7"}


_save, _load = S._save, S._load


# --- pure parts ------------------------------------------------------------------------------------

def is_guitar(name):
    return bool(S.GUITAR.search(pathlib.Path(name).name))


def is_electric(name):
    return is_guitar(name) and not ACOUSTIC.search(pathlib.Path(name).name)


def instrument_key(name):
    """One take's name: the file stem without its track number and a trailing Mic/Amp/Close/DI
    index (`16_ElecGtr1Mic2.wav` -> `ElecGtr1`; a `DT` double stays its own take)."""
    stem = re.sub(r"^\d+_", "", pathlib.Path(name).stem)
    return INSTR_SUFFIX.sub("", stem).lower()


def scenario_plan(tracks, target, sc):
    """{track: pan or None} for a new scenario: the target at its pan, every other guitar-named
    track (stereo ones are folded to mono by `S.place`) by the rule, everything else None."""
    tp, rule, op = NEW[sc]
    others = [t for t in sorted(tracks) if t != target and is_guitar(t)]
    order = []
    for t in others:
        k = instrument_key(t)
        if k not in order:
            order.append(k)
    plan = {t: None for t in tracks}
    plan[target] = tp
    for t in others:
        plan[t] = op if rule == "all" else (op if order.index(instrument_key(t)) % 2 == 0 else -op)
    return plan


def side(p):
    return "C" if p == 0 else ("L" if p < 0 else "R")


def pick(x2, p):
    """The target's channel: L, R, or mid for a centred target."""
    import numpy as np

    x2 = np.asarray(x2, np.float64)
    s = side(p)
    return (x2[0] + x2[1]) / 2 if s == "C" else (x2[0] if s == "L" else x2[1])


def stft(x):
    from scipy.signal import stft as _stft

    return _stft(x, fs=SR, window="hann", nperseg=NFFT, noverlap=NFFT - HOP)[2]


def istft(z, n):
    import numpy as np
    from scipy.signal import istft as _istft

    y = _istft(z, fs=SR, window="hann", nperseg=NFFT, noverlap=NFFT - HOP)[1]
    out = np.zeros(n)
    k = min(n, len(y))
    out[:k] = y[:k]
    return out


def pan_index(zl, zr):
    """Per-bin pan p̂ = 4/π·atan2(|R|, |L|) − 1 (the pan law inverted), and the bin energies."""
    import numpy as np

    al, ar = np.abs(zl), np.abs(zr)
    return 4 / math.pi * np.arctan2(ar, al) - 1, al ** 2 + ar ** 2


def ild_mask(x2, p_t, sigma=SIGMA):
    """Gaussian mask around pan p_t on the per-bin pan index, applied to the target's channel."""
    import numpy as np

    zl, zr = stft(x2[0]), stft(x2[1])
    ph, e = pan_index(zl, zr)
    m = np.exp(-(ph - p_t) ** 2 / (2 * sigma ** 2))
    m[e < FLOOR * e.max()] = 0.0
    s = side(p_t)
    za = (zl + zr) / 2 if s == "C" else (zl if s == "L" else zr)
    return istft(m * za, x2.shape[1])


def coherence_mask(x2, p_t, tau=COH_TAU, k=COH_K, ild=False):
    """Amendment 1: per-bin inter-channel coherence Γ = Re{L·R*}/(|L|·|R| + ε) (the cosine of the
    phase difference), a soft mask 1/(1 + exp(−k(Γ − τ))) applied to the target's channel with the
    mixture phase; with `ild`, multiplied by the ILD mask at p_t. A point source panned anywhere is
    coherent (Γ = 1); different takes on the two sides are not."""
    import numpy as np

    zl, zr = stft(x2[0]), stft(x2[1])
    al, ar = np.abs(zl), np.abs(zr)
    g = np.real(zl * np.conj(zr)) / (al * ar + 1e-20)
    m = 1 / (1 + np.exp(-k * (g - tau)))
    if ild:
        ph, _ = pan_index(zl, zr)
        m = m * np.exp(-(ph - p_t) ** 2 / (2 * SIGMA ** 2))
    m[al ** 2 + ar ** 2 < FLOOR * (al ** 2 + ar ** 2).max()] = 0.0
    s = side(p_t)
    za = (zl + zr) / 2 if s == "C" else (zl if s == "L" else zr)
    return istft(m * za, x2.shape[1])


def wiener(est, x):
    """Step 0's T1: |C|²/(|C|² + |X − C|²) on the mixture channel x, C = est's STFT."""
    import numpy as np

    c, z = stft(est), stft(x)
    pc, pr = np.abs(c) ** 2, np.abs(z - c) ** 2
    return istft(pc / (pc + pr + 1e-20) * z, len(x))


def irm(x, t):
    """The ideal ratio mask on mixture channel x for its target part t (an oracle)."""
    import numpy as np

    zt, z = stft(t), stft(x)
    pt, pr = np.abs(zt) ** 2, np.abs(z - zt) ** 2
    return istft(pt / (pt + pr + 1e-20) * z, len(x))


def blind_peak(x2):
    """The energy-weighted pan-index histogram's peak (41 bins over [−1, 1]), the blind p̃."""
    import numpy as np

    ph, e = pan_index(stft(x2[0]), stft(x2[1]))
    keep = e >= FLOOR * e.max()
    h, edges = np.histogram(ph[keep], bins=HIST_BINS, range=(-1, 1), weights=e[keep])
    k = int(np.argmax(h))
    return float((edges[k] + edges[k + 1]) / 2)


def blind_side(pt):
    return 0.0 if abs(pt) <= 1 / 3 else pt


def si_sdr_db(est, ref):
    import numpy as np

    s, r = np.asarray(est, np.float64), np.asarray(ref, np.float64)
    a = np.dot(s, r) / (np.dot(r, r) + 1e-20)
    t = a * r
    return float(10 * np.log10((np.sum(t ** 2) + 1e-20) / (np.sum((s - t) ** 2) + 1e-20)))


def metrics(est, ref):
    return {"snr": S.snr_db(est, ref), "si_sdr": si_sdr_db(est, ref), "lsd": S.lsd_db(est, ref),
            "bright": S.hf_ratio_db(est) - S.hf_ratio_db(ref)}


def boot_draws(pairs, n=N_BOOT, seed=SEED):
    """`S.band_boot` (same draws), plus the sorted draws themselves."""
    import random
    import statistics as st

    groups = {}
    for band, v in pairs:
        groups.setdefault(band, []).append(v)
    bands = sorted(groups)
    rng = random.Random(seed)
    draws = sorted(st.mean(st.mean(groups[b]) for b in (rng.choice(bands) for _ in bands)) for _ in range(n))
    return S.band_boot(pairs, n, seed), draws


def lobo(pairs):
    """Leave-one-band-out band-weighted means: (min, max)."""
    import statistics as st

    groups = {}
    for band, v in pairs:
        groups.setdefault(band, []).append(v)
    ms = [st.mean(st.mean(groups[b]) for b in groups if b != out) for out in groups]
    return round(min(ms), 3), round(max(ms), 3)


def holm(ps):
    """Holm-adjusted p-values, in the input order."""
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj, run = [0.0] * m, 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * ps[i]))
        adj[i] = run
    return adj


def splitters(st2, mix2, p_t, centre2=None):
    """{splitter: 1-D signal} from a stereo stem crop, the mixture crop, the oracle pan and the
    centre model's output on the stem (or None). M is the baseline (mid)."""
    import numpy as np

    st2 = np.asarray(st2, np.float64)
    out = {"M": (st2[0] + st2[1]) / 2, "a": pick(st2, p_t), "b": (st2[0] - st2[1]) / 2,
           "c": ild_mask(st2, p_t)}
    out["d"] = wiener(out["c"], pick(mix2, p_t))
    if centre2 is not None:
        c2 = np.asarray(centre2, np.float64)
        out["e"] = (c2[0] + c2[1]) / 2
    pb = blind_peak(st2)
    out["f_pick"] = pick(st2, blind_side(pb))
    out["f_mask"] = ild_mask(st2, pb)
    return out, pb


# --- data ------------------------------------------------------------------------------------------

def free_gb():
    return shutil.disk_usage(HOME).free / 1e9


def guard(gb):
    if free_gb() < gb:
        raise SystemExit(f"free disk {free_gb():.2f} GB below the {gb} GB guard (resumable)")


def log_guard(gb, cmd):
    if gb < DEFAULT_DISK_GUARD_GB:
        log = _load(OUT / "log.json") or {}
        log.setdefault("disk_guard_overrides", []).append(
            {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "cmd": cmd, "guard_gb": gb, "default_gb": DEFAULT_DISK_GUARD_GB,
             "free_gb": round(free_gb(), 2),
             "approval": "user, 2026-10-20: 25 GB for this job only; stop below 26 GB"})
        _save(OUT / "log.json", log)
        print(f"DISK GUARD OVERRIDE: {gb} GB (default {DEFAULT_DISK_GUARD_GB})", flush=True)


def build(slug, scenarios=SCENARIOS):
    """{scenario: (mix2 crop, G2 crop)} built in memory from the session tracks (10-s crops), with
    the checks: R's mid = the stored mono context (1e-5), P = the stereo check's P (1e-6)."""
    import numpy as np
    import soundfile as sf

    from analysis import io
    from learn import arm_a_mega53 as A
    from learn import separate as SEP

    part, rec, root = S._session(slug)
    n, a, b = rec["session_frames"], rec["excerpt_start_frame"], rec["excerpt_end_frame"]
    cs, ce = SEP.window(n, a, b, SEP.PAD_S * SR)
    off = a - cs
    tgt = S.target_track(rec, part)
    tracks = rec["included_mix_tracks"]
    stereo = {nm for nm in tracks if sf.info(str(root / nm)).channels >= 2}
    plans = {"R": {t: None for t in tracks}, "P": S.pan_plan(tracks, tgt, stereo)}
    for sc in NEW:
        plans[sc] = scenario_plan(tracks, tgt, sc)
    mix = {sc: np.zeros((2, ce - cs)) for sc in plans}
    g = {sc: np.zeros((2, ce - cs)) for sc in plans}
    for name in tracks:
        au = io.load(root / name)
        assert au.sha256 == rec["verified_source_sha256"][name], (slug, name)
        s = np.asarray(au.samples, np.float64)[:n]
        x = np.zeros((n, s.shape[1]))
        x[:len(s)] = s
        x = x[cs:ce]
        for sc, plan in plans.items():
            y = S.place(x, plan[name])
            mix[sc] += y
            if name == tgt or is_electric(name):
                g[sc] += y
    stored = np.load(A.fdir("contexts", f"{slug}.npy")).astype(np.float64)
    dev_r = float(np.max(np.abs((mix["R"][0] + mix["R"][1]) / 2 - stored)))
    assert dev_r < 1e-5, (slug, dev_r)
    p_st = SMC / "contexts" / f"{slug}-P.npy"
    dev_p = float(np.max(np.abs(mix["P"] - np.load(p_st).astype(np.float64)))) if p_st.exists() else None
    assert dev_p is None or dev_p < 1e-6, (slug, dev_p)
    info = {"offset": off, "target": tgt, "dev_R_mid": dev_r, "dev_P": dev_p,
            "folded_stereo_guitars": sorted(t for t in stereo if is_guitar(t) and t != tgt),
            "plans": {sc: {k: v for k, v in plans[sc].items() if v is not None} for sc in NEW},
            "electric_others": sorted(t for t in tracks if t != tgt and is_electric(t))}
    full = {sc: (mix[sc], g[sc]) for sc in scenarios}
    return full, info


def stem_path(sep, slug, sc):
    if sc in ("R", "P"):
        return SMC / "sep" / sep / f"{slug}-{sc}_stereo.npy"
    return OUT / "sep" / sep / f"{slug}-{sc}.npy"


def cmd_separate(sep, gb, scenarios):
    import numpy as np

    log_guard(gb, f"separate {sep}")
    d = OUT / "sep" / sep
    d.mkdir(parents=True, exist_ok=True)
    log = _load(d / "log.json") or {}
    model = None
    for sc in scenarios:
        for slug, _ in S.parts():
            if stem_path(sep, slug, sc).exists():
                continue
            guard(gb)
            if model is None:
                model = S.StereoSep(sep)
                if sep == "htdemucs":
                    import torch

                    torch.set_num_threads(2)
            full, info = build(slug, (sc,))
            x2 = full[sc][0].astype(np.float32)
            off = info["offset"]
            t = time.time()
            y = model.stereo(x2)[:, off:off + CROP]
            assert y.shape == (2, CROP), (slug, sc, y.shape)
            guard(gb)
            np.save(stem_path(sep, slug, sc), y.astype(np.float32))
            log[f"{slug}|{sc}"] = {"wall_s": round(time.time() - t, 1), "free_gb": round(free_gb(), 2)}
            _save(d / "log.json", log)
            print(sep, sc, slug, log[f"{slug}|{sc}"], flush=True)
    print("SEPARATE DONE", sep)


class Centre:
    """wesleyr36's MDX23C phantom-centre model (MSST v1.0.10 release) on the CPU, 4 threads."""

    def __init__(self, overlap=CENTRE_OVERLAP):
        import torch
        import yaml

        from learn import separator_screen as SCR

        for f, h in CENTRE_FILES.items():
            got = hashlib.sha256((CENTRE_DIR / f).read_bytes()).hexdigest()
            if got != h:
                raise SystemExit(f"hash mismatch: {f}")
        SCR.verify_msst()
        torch.set_num_threads(SCR.THREADS)
        sys.path.insert(0, str(SCR.msst_root() / "repo"))
        SCR.lzma_stub()
        from ml_collections import ConfigDict
        from models.mdx23c_tfc_tdf_v3 import TFC_TDF_net

        with open(CENTRE_DIR / "config_mdx23c_similarity.yaml") as f:
            self.config = ConfigDict(yaml.load(f, Loader=yaml.FullLoader))
        self.model = TFC_TDF_net(self.config)
        st = torch.load(CENTRE_DIR / "model_mdx23c_ep_271_l1_freq_72.2383.ckpt", map_location="cpu")
        self.model.load_state_dict(st.get("state_dict", st))
        self.model.eval()
        self.overlap = overlap

    def __call__(self, x2):
        import numpy as np
        import torch

        from learn import separator_screen as SCR
        from utils.model_utils import demix

        self.config.inference.num_overlap = self.overlap
        n = x2.shape[1]
        y = np.stack([SCR.to44(np.asarray(c, np.float64)) for c in x2]).astype(np.float32)
        with torch.no_grad():
            out = demix(self.config, self.model, y, torch.device("cpu"), "mdx23c", pbar=False)["similarity"]
        return np.stack([SCR.to48(out[c], n) for c in range(2)])


def centre_path(slug, sc, overlap=CENTRE_OVERLAP):
    return OUT / "centre" / f"{slug}-{sc}-ov{overlap}.npy"


def cmd_centre(gb):
    import numpy as np

    log_guard(gb, "centre")
    (OUT / "centre").mkdir(parents=True, exist_ok=True)
    log = _load(OUT / "centre" / "log.json") or {}
    slugs = [s for s, _ in S.parts()]
    jobs = [(s, sc, CENTRE_OVERLAP) for sc in CENTRE_SCEN for s in slugs]
    jobs += [(s, "LC", 8) for s in slugs[:CENTRE_CHECK_PARTS]]
    models = {}
    for slug, sc, ov in jobs:
        if centre_path(slug, sc, ov).exists():
            continue
        src = stem_path("mega53", slug, sc)
        if not src.exists():
            print("missing stem", src, flush=True)
            continue
        guard(gb)
        if ov not in models:
            models[ov] = Centre(ov)
        t = time.time()
        y = models[ov](np.load(src).astype(np.float64))
        np.save(centre_path(slug, sc, ov), y.astype(np.float32))
        log[f"{slug}|{sc}|ov{ov}"] = {"wall_s": round(time.time() - t, 1), "free_gb": round(free_gb(), 2)}
        _save(OUT / "centre" / "log.json", log)
        print("centre", sc, ov, slug, log[f"{slug}|{sc}|ov{ov}"], flush=True)
    print("CENTRE DONE")


def cmd_report():
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import confirm_run as CR

    rows, infos = {}, {}
    for slug, band in S.parts():
        part = A.f_part(slug)
        ref = CR.mono(part["crop"] / "reference.wav")
        full, info = build(slug)
        off = info["offset"]
        infos[slug] = info
        row = {"band": band, "primary": bool(info["electric_others"]), "res": {}, "blind": {}, "anchors": {}}
        for sc in SCENARIOS:
            mix2, g2 = (z[:, off:off + CROP] for z in full[sc])
            p_t = TARGET_PANS[sc]
            gt = S.pan_gains(p_t)
            t_ch = ref if side(p_t) == "C" else ref * (gt[0] if side(p_t) == "L" else gt[1])
            anc = {"mix_mid": (mix2[0] + mix2[1]) / 2, "mix_a": pick(mix2, p_t), "irm": irm(pick(mix2, p_t), t_ch),
                   "G_mid": (g2[0] + g2[1]) / 2, "G_a": pick(g2, p_t), "G_c": ild_mask(g2, p_t)}
            row["anchors"][sc] = {k: metrics(v, ref) for k, v in anc.items()}
            for sep in ("mega53", "htdemucs"):
                sp = stem_path(sep, slug, sc)
                if not sp.exists():
                    continue
                st2 = np.load(sp).astype(np.float64)
                cp = centre_path(slug, sc)
                cen = np.load(cp).astype(np.float64) if sep == "mega53" and cp.exists() else None
                sig, pb = splitters(st2, mix2, p_t, cen)
                m = {k: metrics(v, ref) for k, v in sig.items()}
                if sc == "R":
                    m["mono_fold"] = metrics(np.load(A.sep_crop(sep, slug)).astype(np.float64), ref)
                if sc == "P":
                    m["mono_fold"] = metrics(np.load(SMC / "sep" / sep / f"{slug}-P_mono.npy").astype(np.float64), ref)
                row["res"].setdefault(sep, {})[sc] = m
                row["blind"].setdefault(sep, {})[sc] = {"peak": pb, "side": side(blind_side(pb)),
                                                        "right": side(blind_side(pb)) == side(p_t)}
        if (OUT / "centre" / "log.json").exists():
            c8 = centre_path(slug, "LC", 8)
            if c8.exists() and centre_path(slug, "LC").exists():
                a8, a2 = (np.load(p).astype(np.float64) for p in (c8, centre_path(slug, "LC")))
                row["centre_ov2_vs_ov8_snr_db"] = S.snr_db(a2.mean(0), a8.mean(0))
                row["centre_ov8_e_snr"] = S.snr_db(a8.mean(0), ref)
        rows[slug] = row
        print(slug, "done", flush=True)
    rep = {"rows": rows, "infos": infos, "summary": summarise(rows), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(OUT / "report.json", rep)
    print(json.dumps({k: rep["summary"][k] for k in ("gate", "checks", "verdict")}, indent=1))


def cmd_coherence():
    """Amendment 1: M, c, g and gc on the stored Mega-53 stems of every scenario; writes
    report-coherence.json and leaves report.json alone."""
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import confirm_run as CR

    rows = {}
    for slug, band in S.parts():
        part = A.f_part(slug)
        ref = CR.mono(part["crop"] / "reference.wav")
        full, info = build(slug)
        off = info["offset"]
        row = {"band": band, "primary": bool(info["electric_others"]), "res": {}}
        for sc in SCENARIOS:
            sp = stem_path("mega53", slug, sc)
            if not sp.exists():
                continue
            st2 = np.load(sp).astype(np.float64)
            p_t = TARGET_PANS[sc]
            sig = {"M": (st2[0] + st2[1]) / 2, "c": ild_mask(st2, p_t), "g": coherence_mask(st2, p_t),
                   "gc": coherence_mask(st2, p_t, ild=True)}
            g2 = full[sc][1][:, off:off + CROP]
            sig_g = {"G_g": coherence_mask(g2, p_t), "G_mid": (g2[0] + g2[1]) / 2}
            row["res"][sc] = {k: metrics(v, ref) for k, v in {**sig, **sig_g}.items()}
        rows[slug] = row
        print(slug, "done", flush=True)
    s = {"cells": {}, "gate": []}
    for sc in SCENARIOS:
        for pop in ("primary", "all"):
            for k in COH_SPLITTERS + ("G_g",):
                base = "G_mid" if k == "G_g" else "M"
                cell = {}
                for metric in ("snr", "si_sdr", "lsd", "bright"):
                    pr = [(r["band"], r["res"][sc][k][metric] - r["res"][sc][base][metric]) for r in rows.values()
                          if sc in r["res"] and (pop == "all" or r["primary"])]
                    if pr:
                        cell[metric] = S.band_boot(pr)
                if cell:
                    s["cells"][f"mega53|{sc}|{k}|{pop}"] = cell
    ps = []
    for sc, k in COH_GATED:
        pr = [(r["band"], r["res"][sc][k]["snr"] - r["res"][sc]["M"]["snr"]) for r in rows.values()
              if r["primary"] and sc in r["res"]]
        bb, draws = boot_draws(pr)
        p1 = sum(d <= LOWER_DB for d in draws) / len(draws)
        lsd = S.band_boot([(r["band"], r["res"][sc][k]["lsd"] - r["res"][sc]["M"]["lsd"]) for r in rows.values()
                           if r["primary"] and sc in r["res"]])
        s["gate"].append({"cell": f"{sc}|{k}", "snr": bb, "p_le_1db": p1, "lsd": lsd, "lobo": lobo(pr)})
        ps.append(p1)
    for c, a in zip(s["gate"], holm(ps)):
        c["p_holm"] = a
        c["pass"] = bool(c["snr"]["band_mean"] >= GATE_DB and a < ALPHA and c["lsd"]["band_mean"] <= LSD_GUARD_DB)
        c["stop_side"] = bool(c["snr"]["band_mean"] < STOP_DB or c["snr"]["lo"] <= 0)
    s["verdict"] = ("PASS" if any(c["pass"] for c in s["gate"]) else
                    "STOP" if all(c["stop_side"] for c in s["gate"]) else "GAIN TO BUILD ON")
    rg = s["cells"].get("mega53|R|g|primary", {}).get("snr")
    s["checks"] = {"R_null_g": {"band_mean": rg["band_mean"], "ok": abs(rg["band_mean"]) <= 0.3}} if rg else {}
    old = _load(OUT / "report.json")
    if old:
        s["checks"]["c_matches_report"] = {
            sc: abs(old["summary"]["cells"][f"mega53|{sc}|c|primary"]["snr"]["band_mean"]
                    - s["cells"][f"mega53|{sc}|c|primary"]["snr"]["band_mean"]) <= 0.01
            for sc in ("P", "LC", "HP") if f"mega53|{sc}|c|primary" in old["summary"]["cells"]}
    rep = {"rows": rows, "summary": s, "tau": COH_TAU, "k": COH_K, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(OUT / "report-coherence.json", rep)
    print(json.dumps({k: s[k] for k in ("gate", "checks", "verdict")}, indent=1))


def delta_pairs(rows, sep, sc, k, metric="snr", base="M", pop="primary"):
    out = []
    for r in rows.values():
        if pop == "primary" and not r["primary"]:
            continue
        m = r["res"].get(sep, {}).get(sc)
        if m is None or k not in m:
            continue
        out.append((r["band"], m[k][metric] - m[base][metric]))
    return out


def summarise(rows):
    s = {"cells": {}, "absolute": {}, "anchors": {}, "blind": {}, "checks": {}}
    for sep in ("mega53", "htdemucs"):
        for sc in SCENARIOS:
            for pop in ("primary", "all"):
                for k in SPLITTERS[1:] + ("mono_fold",):
                    cell = {}
                    for metric in ("snr", "si_sdr", "lsd", "bright"):
                        pr = delta_pairs(rows, sep, sc, k, metric, pop=pop)
                        if pr:
                            cell[metric] = S.band_boot(pr)
                    if cell:
                        s["cells"][f"{sep}|{sc}|{k}|{pop}"] = cell
                ab = [(r["band"], r["res"][sep][sc]["M"]["snr"]) for r in rows.values()
                      if sc in r["res"].get(sep, {}) and (pop == "all" or r["primary"])]
                if ab:
                    s["absolute"][f"{sep}|{sc}|M|{pop}"] = S.band_boot(ab)
                bl = [r["blind"][sep][sc]["right"] for r in rows.values()
                      if sc in r["blind"].get(sep, {}) and (pop == "all" or r["primary"])]
                if bl:
                    s["blind"][f"{sep}|{sc}|{pop}"] = {"right": sum(bl), "n": len(bl)}
    for sc in SCENARIOS:
        for pop in ("primary", "all"):
            for k in ("mix_mid", "mix_a", "irm", "G_mid", "G_a", "G_c"):
                pr = [(r["band"], r["anchors"][sc][k]["snr"]) for r in rows.values() if pop == "all" or r["primary"]]
                s["anchors"][f"{sc}|{k}|{pop}"] = S.band_boot(pr)
    # the gate
    cells, ps = [], []
    for sc, k in GATED:
        pr = delta_pairs(rows, "mega53", sc, k)
        if not pr:
            cells.append({"cell": f"{sc}|{k}", "missing": True})
            ps.append(1.0)
            continue
        bb, draws = boot_draws(pr)
        p1 = sum(d <= LOWER_DB for d in draws) / len(draws)
        lsd = S.band_boot(delta_pairs(rows, "mega53", sc, k, "lsd"))
        cells.append({"cell": f"{sc}|{k}", "snr": bb, "p_le_1db": p1, "lsd": lsd, "lobo": lobo(pr)})
        ps.append(p1)
    for c, a in zip(cells, holm(ps)):
        if c.get("missing"):
            continue
        c["p_holm"] = a
        c["pass"] = bool(c["snr"]["band_mean"] >= GATE_DB and a < ALPHA and c["lsd"]["band_mean"] <= LSD_GUARD_DB)
        c["stop_side"] = bool(c["snr"]["band_mean"] < STOP_DB or c["snr"]["lo"] <= 0)
    s["gate"] = cells
    live = [c for c in cells if not c.get("missing")]
    s["verdict"] = ("PASS" if any(c["pass"] for c in live) else
                    "STOP" if live and len(live) == len(cells) and all(c["stop_side"] for c in live) else
                    "GAIN TO BUILD ON" if live else "INCOMPLETE")
    # checks
    smc = _load(SMC / "report.json")
    if smc:
        stored = smc["summary"]["stereo"]["mega53"]["P"]["left"]["band_mean"]
        got = S.band_boot([(r["band"], r["res"]["mega53"]["P"]["a"]["snr"] - r["res"]["mega53"]["P"]["mono_fold"]["snr"])
                           for r in rows.values() if "P" in r["res"].get("mega53", {})])["band_mean"]
        s["checks"]["P_left_minus_mono_all21"] = {"stored": stored, "recomputed": got, "ok": abs(stored - got) <= 0.01}
    rn = s["cells"].get("mega53|R|c|primary", {}).get("snr")
    if rn:
        s["checks"]["R_null_c"] = {"band_mean": rn["band_mean"], "ok": abs(rn["band_mean"]) <= 0.3}
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("separate", "centre", "report", "coherence"))
    ap.add_argument("--sep", choices=("mega53", "htdemucs"), default="mega53")
    ap.add_argument("--scenarios", default="LC,HP,SP", help="new scenarios to separate, in order")
    ap.add_argument("--disk-guard-gb", type=float, default=DEFAULT_DISK_GUARD_GB,
                    help="free-disk floor; below the default 31 GB only with the user's approval (logged)")
    a = ap.parse_args(argv)
    if a.cmd == "separate":
        sc = tuple(x for x in a.scenarios.split(",") if x)
        assert all(x in NEW for x in sc), sc
        cmd_separate(a.sep, a.disk_guard_gb, sc)
    elif a.cmd == "centre":
        cmd_centre(a.disk_guard_gb)
    elif a.cmd == "coherence":
        cmd_coherence()
    else:
        cmd_report()


if __name__ == "__main__":
    main()
