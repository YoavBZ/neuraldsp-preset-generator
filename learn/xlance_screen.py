"""X-LANCE against Mega-53 fast (`docs/xlance-screen-plan.md`). Development data only; zero renders.

    $MSST -m learn.xlance_screen repro        # Mega-53 fast, 4 threads: hashes + 6-clip reproduction
    $MSST -m learn.xlance_screen time-mega    # Mega-53 fast, 2 threads: the 10 timing clips
    $MSST -m learn.xlance_screen xlance       # X-LANCE, 2 threads: audit X, stage F X / X_g / X_ctx
    python -m learn.xlance_screen report      # measures and the declared decision

$MSST is ~/ndsp-presets/tools/msst-venv/bin/python; run separations under `nice -n 10`, CPU only.
Weights and code: ~/ndsp-presets/tools/xlance (manifest.json). Outputs: ~/ndsp-presets/learn/xlance-screen/.
Gate 1's Mega-53 stems (~/ndsp-presets/learn/direct-stems/gate1/stems/mega53) are only read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import random
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
OUT = HOME / "learn/xlance-screen"
XL = HOME / "tools/xlance"
GATE1 = HOME / "learn/direct-stems/gate1/stems/mega53"
FAST_HASHES = HOME / "learn/direct-stems/sepcheck/fast-stem-hashes.json"
G_DIR = HOME / "learn/separation-finetune/G/crop"
SR, SR44 = 48000, 44100
CROP = 480_000
CHUNK44, OVERLAP44 = 441_000, 44_100     # X-LANCE: 10-s chunks, 1-s crossfade (inference_full.py)
SEED = 20261082                          # reproduction and timing clips
N_REPRO, N_TIME = 3, 10
REPRO_DB = 100.0
LAG_TOL = 3
THREADS = 2
REPRO_THREADS = 4                        # gate 1's setting
DISK_GUARD_GB = 31.0
MEL_LO, MEL_HI = 30.0, 16000.0           # song_aug.FMIN, FMAX: the direct model's mel range
HF_SPLIT_HZ = 3000.0
COST_RATIO = 1.5
BOOT_SEED, N_BOOT = 20261019, 4000


def _save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1) + "\n")
    tmp.replace(path)


def _load(path):
    return json.loads(path.read_text()) if path.exists() else None


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


# --- pure parts ----------------------------------------------------------------------------------

def chunk_starts(n, chunk=CHUNK44, overlap=OVERLAP44):
    """Chunk starts covering n samples with hop chunk - overlap; the last chunk may run past n."""
    hop = chunk - overlap
    if n <= chunk:
        return [0]
    k = math.ceil((n - overlap) / hop)
    return [i * hop for i in range(k)]


def crossfade_windows(starts, chunk=CHUNK44, overlap=OVERLAP44):
    """Per-chunk weights: linear crossfades on interior overlaps only, so they sum to 1 everywhere
    (inference_full.py also faded the outer edges to zero; that is not kept)."""
    import numpy as np

    ws = []
    for i, _ in enumerate(starts):
        w = np.ones(chunk)
        if i > 0:
            w[:overlap] = np.linspace(0, 1, overlap)
        if i < len(starts) - 1:
            w[-overlap:] = np.linspace(1, 0, overlap)
        ws.append(w)
    return ws


def run_chunked(f, a, chunk=CHUNK44, overlap=OVERLAP44):
    """f on (c, n) audio in crossfaded chunks; f maps (c, chunk) -> (c, chunk). Exact single pass
    when n == chunk."""
    import numpy as np

    c, n = a.shape
    starts = chunk_starts(n, chunk, overlap)
    total = starts[-1] + chunk
    pad = np.zeros((c, total), a.dtype)
    pad[:, :n] = a
    out = np.zeros((c, total))
    for s, w in zip(starts, crossfade_windows(starts, chunk, overlap)):
        out[:, s:s + chunk] += np.asarray(f(pad[:, s:s + chunk]), np.float64) * w
    return out[:, :n]


def repro_db(stored, new):
    """Plain (not gain-fitted) SNR of new against stored."""
    import numpy as np

    s, x = np.asarray(stored, np.float64), np.asarray(new, np.float64)
    return float(10 * np.log10(np.sum(s ** 2) / (np.sum((s - x) ** 2) + 1e-30)))


def mel_lsd_db(x, ref):
    from learn import stereo_mix_check as SMC

    import numpy as np

    d = SMC.third_octave_db(x, lo=MEL_LO, hi=MEL_HI) - SMC.third_octave_db(ref, lo=MEL_LO, hi=MEL_HI)
    return float(np.sqrt(np.mean((d - d.mean()) ** 2)))


def band_centres(lo=MEL_LO, hi=MEL_HI):
    """The 1/3-octave centres `third_octave_db` keeps for these limits (same order)."""
    out = []
    for k in range(-30, 30):
        c = 1000 * 2 ** (k / 3)
        if c / 2 ** (1 / 6) >= lo and c * 2 ** (1 / 6) <= hi:
            out.append(c)
    return out


def spectral_error(x, ref):
    """Gain-removed 1/3-octave error (dB) of x against ref over the mel range."""
    from learn import stereo_mix_check as SMC

    d = SMC.third_octave_db(x, lo=MEL_LO, hi=MEL_HI) - SMC.third_octave_db(ref, lo=MEL_LO, hi=MEL_HI)
    return d - d.mean()


def measures(x, ref):
    from learn import separation_ceiling as SC

    m = SC.measures(x, ref)
    m["mel_lsd_db"] = mel_lsd_db(x, ref)
    return m


def decide(snr, lsd, cost_ratio):
    """The declared rule. snr, lsd: {'mean', 'lo90', 'hi90'} of X - M_f on the audit mixes."""
    q = snr["mean"] >= 0 and snr["hi90"] is not None and snr["hi90"] >= 0 and \
        lsd["hi90"] is not None and lsd["hi90"] < 0
    if not q:
        return "KEEP MEGA-53"
    return "SWITCH TO X-LANCE" if cost_ratio <= COST_RATIO else "PASS, OVER BUDGET"


def spread(errs, centres):
    """Across-clip spread of the spectral error: per band median, SD and IQR; and the SD of each
    clip's mean error above HF_SPLIT_HZ."""
    import numpy as np

    E = np.asarray(errs, np.float64)
    hf = np.asarray(centres) > HF_SPLIT_HZ
    hfm = E[:, hf].mean(1)
    q75, q25 = np.percentile(E, [75, 25], axis=0)
    return {"centres_hz": [round(c, 1) for c in centres], "median_db": np.median(E, 0).round(2).tolist(),
            "sd_db": E.std(0, ddof=1).round(2).tolist(), "iqr_db": (q75 - q25).round(2).tolist(),
            "hf_mean_db_median": round(float(np.median(hfm)), 2), "hf_mean_db_sd": round(float(hfm.std(ddof=1)), 2)}


# --- data ----------------------------------------------------------------------------------------

def audit_rows():
    from learn import direct_stems as DS

    return DS.audit_rows()


def audit_mix_ref(r):
    from learn import direct_stems as DS

    y, bm, _, _ = DS.audit_audio(r)
    return y + bm, y


def f_slugs():
    from learn import arm_a_mega53 as A

    return A.pool_slugs()


def f_mix_ref(slug):
    from learn import arm_a_mega53 as A
    from learn import confirm_run as CR

    crop = A.f_part(slug)["crop"]
    return CR.mono(crop / "mix.wav"), CR.mono(crop / "reference.wav")


def f_context(slug):
    import numpy as np

    from learn import arm_a_mega53 as A

    off = json.loads(A.fdir("contexts", "log.json").read_text())[slug]["offset"]
    return np.load(A.fdir("contexts", f"{slug}.npy")).astype(np.float64), off


def picks():
    """(3 audit ids, 3 stage F slugs, 10 timing audit ids), seed 20261082."""
    rng = random.Random(SEED)
    ids = sorted(r["i"] for r in audit_rows())
    a = sorted(rng.sample(ids, N_REPRO))
    f = sorted(rng.sample(f_slugs(), N_REPRO))
    t = sorted(rng.sample(ids, N_TIME))
    return a, f, t


def m_stem(kind, key):
    import numpy as np

    return np.load(GATE1 / kind / f"{key}.npy").astype(np.float64)


def x_path(row, kind, key):
    return OUT / "stems" / row / kind / f"{key}.npy"


def disk_check():
    from learn import pretrain_set as PS

    if not PS.disk_ok(guard=DISK_GUARD_GB):
        raise SystemExit(f"free disk below {DISK_GUARD_GB} GB")


# --- separators (msst-venv) ----------------------------------------------------------------------

def mega53(threads):
    import torch

    from learn import direct_stems as DS

    run = _load(GATE1 / "run.json")
    if not (run["fast"] and run["chunk_size"] == DS.FAST_CHUNK and run["num_overlap"] == DS.FAST_OVERLAP
            and run["info"]["pruned"]):
        raise SystemExit("gate 1's run.json is not pruned Mega-53 fast")
    s = DS.separator("mega53")
    torch.set_num_threads(threads)
    return s


class XLance:
    """X-LANCE on mono 48-kHz audio: two equal channels, 44.1 kHz, each model in crossfaded 10-s
    chunks, mean of the output channels, back to 48 kHz."""

    def __init__(self, names, threads=THREADS):
        import torch

        from learn import separator_screen as SCR      # noqa: F401  (its lzma stub, before librosa)

        man = json.loads((XL / "manifest.json").read_text())
        torch.set_num_threads(threads)
        os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "0"
        sys.path.insert(0, str(XL / "code"))
        cwd = os.getcwd()
        os.chdir(XL / "code")                         # configs are read from ./configs
        try:
            from inference import load_config_and_state_dict, load_generator
            self.models = []
            for n in names:
                w = next(f for f in man["weights"] if f["name"] == f"{n}.pth")
                if sha256(XL / w["path"]) != w["sha256"]:
                    raise SystemExit(f"{n}: hash mismatch")
                cfg, sd = load_config_and_state_dict(str(XL / w["path"]), "cpu")
                assert cfg["data"]["sample_rate"] == SR44
                self.models.append(load_generator(cfg, sd, device="cpu"))
        finally:
            os.chdir(cwd)
        self.names = list(names)

    def _f(self, model):
        import numpy as np
        import torch

        def f(a):
            with torch.no_grad():
                y = model(torch.from_numpy(np.ascontiguousarray(a, np.float32))[None])[0].numpy()
            out = np.zeros(a.shape)
            k = min(a.shape[1], y.shape[-1])
            out[:, :k] = y.reshape(a.shape[0], -1)[:, :k]
            return out
        return f

    def __call__(self, x):
        import numpy as np

        from learn import separator_screen as SCR

        y = SCR.to44(np.asarray(x, np.float64))
        a = np.stack([y, y])
        for m in self.models:
            a = run_chunked(self._f(m), a)
        return SCR.to48(a.mean(0), len(x))


def timed(sep, x):
    t, c = time.time(), time.process_time()
    s = sep(x)
    return s, time.time() - t, time.process_time() - c


def cmd_repro():
    import numpy as np

    disk_check()
    a, f, _ = picks()
    old = json.loads(FAST_HASHES.read_text())
    rows = {r["i"]: r for r in audit_rows()}
    bad = [i for i in rows if sha256(GATE1 / "audit" / f"{i}.npy") != old[str(i)]]
    if bad:
        raise SystemExit(f"gate 1 audit stems changed: {bad[:5]}")
    f_hashes = {s: sha256(GATE1 / "stagef" / f"{s}.npy") for s in f_slugs()}
    prev = _load(OUT / "stagef-stem-hashes.json")
    if prev is not None and prev != f_hashes:
        raise SystemExit("gate 1 stage F stems changed since recorded")
    _save(OUT / "stagef-stem-hashes.json", f_hashes)
    sep = mega53(REPRO_THREADS)
    rep = {"seed": SEED, "threads": REPRO_THREADS, "min_db": REPRO_DB, "audit_hashes_ok": len(rows), "rows": {}}
    for kind, key in [("audit", i) for i in a] + [("stagef", s) for s in f]:
        x = audit_mix_ref(rows[key])[0] if kind == "audit" else f_mix_ref(key)[0]
        s, wall, cpu = timed(sep, x)
        db = repro_db(m_stem(kind, key), s)
        rep["rows"][f"{kind}/{key}"] = {"db": round(db, 2), "wall_s": round(wall, 1), "cpu_s": round(cpu, 1)}
        print(f"repro {kind} {key}: {db:.1f} dB ({wall:.1f} s)", flush=True)
    rep["ok"] = all(v["db"] >= REPRO_DB for v in rep["rows"].values())
    _save(OUT / "repro.json", rep)
    if not rep["ok"]:
        raise SystemExit("REPRO FAIL: a stored Mega-53 fast stem did not reproduce at >= 100 dB")
    print("REPRO OK")


def cmd_time_mega():
    disk_check()
    _, _, t = picks()
    rows = {r["i"]: r for r in audit_rows()}
    sep = mega53(THREADS)
    out = {"threads": THREADS, "clips": {}}
    for i in t:
        s, wall, cpu = timed(sep, audit_mix_ref(rows[i])[0])
        out["clips"][str(i)] = {"wall_s": round(wall, 2), "cpu_s": round(cpu, 2),
                                "db_vs_stored": round(repro_db(m_stem("audit", i), s), 1)}
        print(f"mega53 {i}: {wall:.1f} s wall, {cpu:.1f} s CPU", flush=True)
    _save(OUT / "time-mega53.json", out)


def cmd_xlance():
    import numpy as np

    from learn import rank_margin as RM

    disk_check()
    if not (_load(OUT / "repro.json") or {}).get("ok"):
        raise SystemExit("run repro first")
    _, _, t = picks()
    rows = {r["i"]: r for r in audit_rows()}
    log_p = OUT / "xlance-log.json"
    log = _load(log_p) or {}
    chain, alone = XLance(["denoise", "gtr_mss"]), None

    def one(row, kind, key, sep, x, ref, crop_off=None):
        p = x_path(row, kind, key)
        if p.exists():
            return
        s, wall, cpu = timed(sep, x)
        if crop_off is not None:
            s = s[crop_off:crop_off + CROP]
        if len(s) != len(ref) or not np.isfinite(s).all():
            raise SystemExit(f"{row} {kind} {key}: bad stem")
        lag = RM.gcc_lag(s, ref)
        log[f"{row}/{kind}/{key}"] = {"wall_s": round(wall, 2), "cpu_s": round(cpu, 2), "lag": lag,
                                      "len_in": len(x)}
        if abs(lag) > LAG_TOL:
            _save(log_p, log)
            raise SystemExit(f"{row} {kind} {key}: lag {lag} samples beyond ±{LAG_TOL}; stopping")
        p.parent.mkdir(parents=True, exist_ok=True)
        np.save(p.with_suffix(".tmp.npy"), s.astype(np.float32))
        p.with_suffix(".tmp.npy").replace(p)
        _save(log_p, log)
        print(f"{row} {kind} {key}: {wall:.1f} s wall, {cpu:.1f} s CPU, lag {lag}", flush=True)

    order = t + [i for i in sorted(rows) if i not in t]           # the timing clips first
    for n, i in enumerate(order):
        if n % 10 == 0:
            disk_check()
        x, y = audit_mix_ref(rows[i])
        one("X", "audit", i, chain, x, y)
    for s in f_slugs():
        x, ref = f_mix_ref(s)
        one("X", "stagef", s, chain, x, ref)
    alone = XLance(["gtr_mss"])
    for s in f_slugs():
        x, ref = f_mix_ref(s)
        one("X_g", "stagef", s, alone, x, ref)
    for s in f_slugs():
        ctx, off = f_context(s)
        x, ref = f_mix_ref(s)
        if float(np.max(np.abs(ctx[off:off + CROP] - x))) > 1e-4:
            raise SystemExit(f"{s}: context slice differs from mix.wav")
        one("X_ctx", "stagef", s, chain, ctx, ref, crop_off=off)
    print("XLANCE DONE")


# --- report (no torch) ---------------------------------------------------------------------------

MUSDB_AUDIT_BANDS = ("Hollow Ground",)                  # Ill Fate (MUSDB18 test)
CAMBRIDGE = "cambridge"


def readout(pairs, clustered):
    """pairs: [(band, key, value)]. Band-weighted mean with the deciding interval and the bootstrap."""
    from learn import direct_stems as DS
    from learn import stereo_mix_check as SMC

    b = SMC.band_boot([(band, v) for band, _, v in pairs], n=N_BOOT, seed=BOOT_SEED)
    out = {"bootstrap": b}
    if clustered:
        out["t"] = DS.t_interval(pairs)
    return out


def lobo_min(pairs):
    import statistics as st

    bands = sorted({b for b, _, _ in pairs})
    if len(bands) < 3:
        return None
    vals = []
    for drop in bands:
        g = {}
        for b, _, v in pairs:
            if b != drop:
                g.setdefault(b, []).append(v)
        vals.append(st.mean(st.mean(v) for v in g.values()))
    return {"min": round(min(vals), 3), "max": round(max(vals), 3)}


def cmd_report():
    import numpy as np

    from learn import separation_ceiling as SC
    from learn import locator_truth as LT

    rows = {r["i"]: r for r in audit_rows()}
    log = _load(OUT / "xlance-log.json")
    rep = {"plan": "docs/xlance-screen-plan.md", "time": time.strftime("%Y-%m-%d %H:%M:%S"), "renders": 0,
           "repro": _load(OUT / "repro.json"), "audit": {}, "stagef": {}}
    centres = band_centres()
    # audit
    per = {}
    errs = {"M_f": [], "X": [], "mix": []}
    for i, r in rows.items():
        x, y = audit_mix_ref(r)
        sig = {"M_f": m_stem("audit", i), "X": np.load(x_path("X", "audit", i)).astype(np.float64), "mix": x}
        per[i] = {"band": r["band"], "section": r["section"], **{k: measures(v, y) for k, v in sig.items()}}
        for k in errs:
            errs[k].append(spectral_error(sig[k], y))
    _save(OUT / "audit-per-clip.json", {str(k): v for k, v in per.items()})
    MEAS = ("snr_db", "mel_lsd_db", "lsd_db", "bright_diff_db", "si_sdr_db")
    a = rep["audit"]
    a["levels"] = {k: {m: readout([(p["band"], i, p[k][m]) for i, p in per.items()], True)["t"]["mean"]
                       for m in MEAS} for k in ("M_f", "X", "mix")}

    def deltas(keep):
        return {m: {**readout([(p["band"], i, p["X"][m] - p["M_f"][m]) for i, p in per.items() if keep(i, p)], True),
                    "lobo": lobo_min([(p["band"], i, p["X"][m] - p["M_f"][m]) for i, p in per.items() if keep(i, p)])}
                for m in MEAS}

    a["delta_X_minus_Mf"] = deltas(lambda i, p: True)
    a["delta_without_musdb"] = deltas(lambda i, p: p["band"] not in MUSDB_AUDIT_BANDS)
    a["delta_without_cambridge"] = {m: {"points_by_band": {b: round(float(np.mean([p["X"][m] - p["M_f"][m] for p in per.values() if p["band"] == b])), 3)
                                                           for b in sorted({p["band"] for p in per.values() if not p["section"].startswith(CAMBRIDGE)})}}
                                    for m in MEAS}
    a["spread"] = {k: spread(v, centres) for k, v in errs.items()}
    # cost
    tm = _load(OUT / "time-mega53.json")
    tx = {k.split("/")[-1]: v for k, v in log.items() if k.startswith("X/audit/")}
    ids = list(tm["clips"])
    cm = float(np.mean([tm["clips"][k]["cpu_s"] for k in ids]))
    cx = float(np.mean([tx[k]["cpu_s"] for k in ids]))
    wm = float(np.mean([tm["clips"][k]["wall_s"] for k in ids]))
    wx = float(np.mean([tx[k]["wall_s"] for k in ids]))
    rep["cost"] = {"clips": ids, "threads": THREADS, "mega53_cpu_s": round(cm, 1), "x_cpu_s": round(cx, 1),
                   "ratio_cpu": round(cx / cm, 2), "mega53_wall_s": round(wm, 1), "x_wall_s": round(wx, 1),
                   "ratio_wall": round(wx / wm, 2), "limit": COST_RATIO,
                   "build_budget_h_scaled": [round(13 * cx / cm, 1), round(17 * cx / cm, 1)]}
    d = a["delta_X_minus_Mf"]
    rep["decision"] = decide({"mean": d["snr_db"]["t"]["mean"], "hi90": d["snr_db"]["t"]["hi90"]},
                             {"hi90": d["mel_lsd_db"]["t"]["hi90"]}, rep["cost"]["ratio_cpu"])
    # stage F (descriptive)
    tab = SC.load_table()
    fper = {}
    ferr = {"M_f": [], "X": []}
    for s in f_slugs():
        x, ref = f_mix_ref(s)
        G = np.load(G_DIR / f"{s}.npy").astype(np.float64)
        sig = {"M_f": m_stem("stagef", s), "G": G, "mix": x,
               **{k: np.load(x_path(k, "stagef", s)).astype(np.float64) for k in ("X", "X_g", "X_ctx")}}
        e = tab["stage_f"][s]
        other = any(v in ("double_track_of_target", "double_track_of_other", "other_electric_guitar")
                    for v in e["tracks"].values())
        fper[s] = {"band": e["band"], "other_guitar": other, **{k: measures(v, ref) for k, v in sig.items()},
                   "vs_G": {k: measures(sig[k], G) for k in ("M_f", "X", "X_g", "X_ctx")}}
        for k in ferr:
            ferr[k].append(spectral_error(sig[k], ref))
    _save(OUT / "stagef-per-part.json", fper)
    musdb = set(LT.MUSDB_TRAIN) | set(LT.MUSDB_TEST)
    norm = lambda s: s.replace("_", " ").replace("-", " ").lower()                           # noqa: E731
    is_musdb = lambda s: any(norm(m) in norm(s) for m in musdb)                              # noqa: E731
    pops = {"all21": lambda s: True, "other19": lambda s: fper[s]["other_guitar"],
            "without_musdb": lambda s: not is_musdb(s)}
    f = rep["stagef"]
    f["counts"] = {k: sum(map(v, fper)) for k, v in pops.items()}
    for pop, keep in pops.items():
        f[pop] = {"levels": {k: {m: SC_boot([(fper[s]["band"], fper[s][k][m]) for s in fper if keep(s)])
                                 for m in MEAS} for k in ("M_f", "X", "X_g", "X_ctx", "G", "mix")},
                  "delta_vs_Mf": {k: {m: SC_boot([(fper[s]["band"], fper[s][k][m] - fper[s]["M_f"][m]) for s in fper if keep(s)])
                                      for m in MEAS} for k in ("X", "X_g", "X_ctx", "G")}}
    f["vs_G_snr"] = {k: SC_boot([(fper[s]["band"], fper[s]["vs_G"][k]["snr_db"]) for s in fper]) for k in ("M_f", "X", "X_g", "X_ctx")}
    f["spread"] = {k: spread(v, centres) for k, v in ferr.items()}
    f["lags"] = {k: v["lag"] for k, v in log.items()}
    _save(OUT / "report.json", rep)
    t = d["snr_db"]["t"]
    l = d["mel_lsd_db"]["t"]
    print(f"audit X - M_f: SNR {t['mean']:+.3f} [{t['lo90']:+.3f}, {t['hi90']:+.3f}]; "
          f"mel LSD {l['mean']:+.3f} [{l['lo90']:+.3f}, {l['hi90']:+.3f}]; cost x{rep['cost']['ratio_cpu']}")
    print(f"XLANCE SCREEN: {rep['decision']}")


def SC_boot(pairs):
    from learn import stereo_mix_check as SMC

    return SMC.band_boot(pairs, n=N_BOOT, seed=BOOT_SEED)


# --- Amendment 1: gtr_mss alone (X_g) on the audit mixes ----------------------------------------------

SNR_FAIL_DB, LSD_FAIL_DB = 3.0, 5.0
STORED_MEGA_CPU_S = 29.7


def failures(per, row, base="M_f"):
    """Clips where `row` or `base` is clearly worse than the other. per: {key: {row: measures}}."""
    out = {"row_snr_worse": [], "base_snr_worse": [], "row_lsd_worse": [], "base_lsd_worse": []}
    for k, p in per.items():
        ds = p[row]["snr_db"] - p[base]["snr_db"]
        dl = p[row]["mel_lsd_db"] - p[base]["mel_lsd_db"]
        if ds < -SNR_FAIL_DB:
            out["row_snr_worse"].append(k)
        if ds > SNR_FAIL_DB:
            out["base_snr_worse"].append(k)
        if dl > LSD_FAIL_DB:
            out["row_lsd_worse"].append(k)
        if dl < -LSD_FAIL_DB:
            out["base_lsd_worse"].append(k)
    return {**{f"{n}": sorted(v, key=str) for n, v in out.items()}, **{f"n_{n}": len(v) for n, v in out.items()}}


def decide_a1(xg_q, xg_cost_ok, x_q, x_cost_ok, xg_minus_x_lsd_lo):
    """Amendment 1's verdict on CPU legs. *_q: quality legs pass; xg_minus_x_lsd_lo: the lower bound of
    X_g - X mel-range LSD (X clearly better on tone if > 0)."""
    xg, x = xg_q and xg_cost_ok, x_q and x_cost_ok
    if xg and x:
        pick = "X" if xg_minus_x_lsd_lo is not None and xg_minus_x_lsd_lo > 0 else "X_g"
    elif xg:
        pick = "X_g"
    elif x:
        pick = "X"
    else:
        if xg_q and not xg_cost_ok:
            return "X_g: PASS, OVER BUDGET; KEEP MEGA-53"
        return "KEEP MEGA-53"
    return f"{pick} PASSES THE CPU LEGS: PENDING MPS TIMING (Mega-53 stays the fallback)"


def quality_ok(snr_t, lsd_t):
    return snr_t["mean"] >= 0 and snr_t["hi90"] is not None and snr_t["hi90"] >= 0 and \
        lsd_t["hi90"] is not None and lsd_t["hi90"] < 0


def _purge(names=("models", "inference")):
    for k in list(sys.modules):
        if k in names or any(k.startswith(n + ".") for n in names):
            del sys.modules[k]


def cmd_xlance_g():
    import numpy as np

    from learn import rank_margin as RM

    disk_check()
    if not (_load(OUT / "repro.json") or {}).get("ok"):
        raise SystemExit("run repro first")
    _, _, t = picks()
    rows = {r["i"]: r for r in audit_rows()}
    mega = mega53(THREADS)
    warm_x = audit_mix_ref(rows[t[0]])[0]
    mega(warm_x)                                     # untimed warm-up; caches MSST's utils
    _purge()                                         # MSST's `models`/`inference` out of the way
    xg = XLance(["gtr_mss"])
    xg(warm_x)                                       # untimed warm-up
    log_p = OUT / "xlance-g-log.json"
    log = _load(log_p) or {}

    def save(key, s, y, wall, cpu):
        lag = RM.gcc_lag(s, y)
        log[f"X_g/audit/{key}"] = {"wall_s": round(wall, 2), "cpu_s": round(cpu, 2), "lag": lag}
        _save(log_p, log)
        if len(s) != len(y) or not np.isfinite(s).all() or abs(lag) > LAG_TOL:
            raise SystemExit(f"X_g audit {key}: bad stem or lag {lag}; stopping")
        p = x_path("X_g", "audit", key)
        p.parent.mkdir(parents=True, exist_ok=True)
        np.save(p.with_suffix(".tmp.npy"), s.astype(np.float32))
        p.with_suffix(".tmp.npy").replace(p)
        print(f"X_g audit {key}: {wall:.1f} s wall, {cpu:.1f} s CPU, lag {lag}", flush=True)

    tm = {"threads": THREADS, "interleaved": True, "clips": {}}
    for i in t:                                       # Mega-53, then X_g, clip by clip
        x, y = audit_mix_ref(rows[i])
        s, wall, cpu = timed(mega, x)
        db = repro_db(m_stem("audit", i), s)
        tm["clips"][str(i)] = {"wall_s": round(wall, 2), "cpu_s": round(cpu, 2), "db_vs_stored": round(db, 1)}
        _save(OUT / "time-mega53-a1.json", tm)
        print(f"mega53 {i}: {wall:.1f} s wall, {cpu:.1f} s CPU, {db:.0f} dB vs stored", flush=True)
        if db < REPRO_DB:
            raise SystemExit(f"Mega-53 {i}: {db:.1f} dB against gate 1's stem; stopping")
        s, wall, cpu = timed(xg, x)
        save(i, s, y, wall, cpu)
    for n, i in enumerate(sorted(k for k in rows if k not in t)):
        if n % 10 == 0:
            disk_check()
        if x_path("X_g", "audit", i).exists():
            continue
        x, y = audit_mix_ref(rows[i])
        s, wall, cpu = timed(xg, x)
        save(i, s, y, wall, cpu)
    print("XLANCE-G DONE")


def cmd_report_a1():
    import numpy as np

    rows = {r["i"]: r for r in audit_rows()}
    old = {int(k): v for k, v in json.loads((OUT / "audit-per-clip.json").read_text()).items()}
    per = {}
    errs = []
    for i, r in rows.items():
        x, y = audit_mix_ref(r)
        g = np.load(x_path("X_g", "audit", i)).astype(np.float64)
        per[i] = {**old[i], "X_g": measures(g, y)}
        errs.append(spectral_error(g, y))
    _save(OUT / "audit-per-clip-a1.json", {str(k): v for k, v in per.items()})
    MEAS = ("snr_db", "mel_lsd_db", "lsd_db", "bright_diff_db", "si_sdr_db")

    def deltas(a, b, keep=lambda p: True):
        out = {}
        for m in MEAS:
            pairs = [(p["band"], i, p[a][m] - p[b][m]) for i, p in per.items() if keep(p)]
            out[m] = {**readout(pairs, True), "lobo": lobo_min(pairs)}
        return out

    rep = {"label": "Amendment 1, post-result second variant", "time": time.strftime("%Y-%m-%d %H:%M:%S"),
           "renders": 0, "audit": {}}
    a = rep["audit"]
    a["levels_X_g"] = {m: readout([(p["band"], i, p["X_g"][m]) for i, p in per.items()], True)["t"]["mean"] for m in MEAS}
    a["Xg_minus_Mf"] = deltas("X_g", "M_f")
    a["Xg_minus_X"] = deltas("X_g", "X")
    a["X_minus_Mf"] = deltas("X", "M_f")
    a["Xg_minus_Mf_without_musdb"] = deltas("X_g", "M_f", lambda p: p["band"] not in MUSDB_AUDIT_BANDS)
    a["Xg_minus_Mf_without_cambridge_points"] = {
        m: {b: round(float(np.mean([p["X_g"][m] - p["M_f"][m] for p in per.values() if p["band"] == b])), 3)
            for b in sorted({p["band"] for p in per.values() if not p["section"].startswith(CAMBRIDGE)})} for m in MEAS}
    a["spread_X_g"] = spread(errs, band_centres())
    # failures, both variants, both sets
    fper = json.loads((OUT / "stagef-per-part.json").read_text())
    rep["failures"] = {"audit": {v: failures(per, v) for v in ("X", "X_g")},
                       "stagef": {v: failures(fper, v) for v in ("X", "X_g")}}
    # cost: same-session interleaved Mega-53 against X_g, the same 10 clips
    tm = _load(OUT / "time-mega53-a1.json")
    lg = _load(OUT / "xlance-g-log.json")
    lx = _load(OUT / "xlance-log.json")
    ids = list(tm["clips"])
    cm = float(np.mean([tm["clips"][k]["cpu_s"] for k in ids]))
    cg = float(np.mean([lg[f"X_g/audit/{k}"]["cpu_s"] for k in ids]))
    cx = float(np.mean([lx[f"X/audit/{k}"]["cpu_s"] for k in ids]))
    wm = float(np.mean([tm["clips"][k]["wall_s"] for k in ids]))
    wg = float(np.mean([lg[f"X_g/audit/{k}"]["wall_s"] for k in ids]))
    rep["cost"] = {"clips": ids, "mega53_cpu_s_same_session": round(cm, 1), "x_g_cpu_s": round(cg, 1),
                   "ratio_same_session": round(cg / cm, 2), "ratio_vs_stored_29_7": round(cg / STORED_MEGA_CPU_S, 2),
                   "x_cpu_s_first_run": round(cx, 1), "x_ratio_vs_same_session_mega": round(cx / cm, 2),
                   "mega53_wall_s": round(wm, 1), "x_g_wall_s": round(wg, 1), "ratio_wall": round(wg / wm, 2),
                   "limit": COST_RATIO, "lags_max_abs": max(abs(v["lag"]) for v in lg.values())}
    t = lambda d, m: d[m]["t"]                                                                # noqa: E731
    xg_q = quality_ok(t(a["Xg_minus_Mf"], "snr_db"), t(a["Xg_minus_Mf"], "mel_lsd_db"))
    x_q = quality_ok(t(a["X_minus_Mf"], "snr_db"), t(a["X_minus_Mf"], "mel_lsd_db"))
    rep["legs"] = {"X_g_quality": xg_q, "X_g_cost": cg / cm <= COST_RATIO, "X_quality": x_q,
                   "X_cost_first_run": False}
    rep["decision"] = decide_a1(xg_q, cg / cm <= COST_RATIO, x_q, False, t(a["Xg_minus_X"], "mel_lsd_db")["lo90"])
    _save(OUT / "report-a1.json", rep)
    s, l = t(a["Xg_minus_Mf"], "snr_db"), t(a["Xg_minus_Mf"], "mel_lsd_db")
    fa = rep["failures"]["audit"]["X_g"]
    print(f"audit X_g - M_f: SNR {s['mean']:+.3f} [{s['lo90']:+.3f}, {s['hi90']:+.3f}]; mel LSD {l['mean']:+.3f} "
          f"[{l['lo90']:+.3f}, {l['hi90']:+.3f}]; cost x{rep['cost']['ratio_same_session']} same session; "
          f"failures X_g/M_f SNR {fa['n_row_snr_worse']}/{fa['n_base_snr_worse']}")
    print(f"AMENDMENT 1: {rep['decision']}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("repro", "time-mega", "xlance", "report", "xlance-g", "report-a1"))
    a = ap.parse_args(argv)
    {"repro": cmd_repro, "time-mega": cmd_time_mega, "xlance": cmd_xlance, "report": cmd_report,
     "xlance-g": cmd_xlance_g, "report-a1": cmd_report_a1}[a.cmd]()


if __name__ == "__main__":
    main()
