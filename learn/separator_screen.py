"""The separator screen (`docs/separator-screen-plan.md`, DI-recovery experiment 1). Development only.

    .venv/bin/python -m learn.separator_screen contexts            # 30-s backings and DIs, line-up checks
    .venv/bin/python -m learn.separator_screen fakes               # 20 renders: warm-up S, T on the 30-s DI
    $TORCH_PY -m learn.separator_screen separate --row htdemucs    # CPU, 4 threads, renderer idle
    $MSST_PY  -m learn.separator_screen identity                   # pruned head == full model, once
    $MSST_PY  -m learn.separator_screen separate --row mega53      # CPU, alone; peak RSS and swap logged
    .venv/bin/python -m learn.separator_screen blend               # the crossover; lag checks
    $TORCH_PY -m learn.separator_screen rebuild                    # the part's fold C′ (CPU)
    .venv/bin/python -m learn.separator_screen render              # ≈120 renders, hard stop at 170 in all
    .venv/bin/python -m learn.separator_screen report              # the screen, the reading, fragility

TORCH_PY is ~/ndsp-presets/tools/demucs-venv/bin/python; MSST_PY is
~/ndsp-presets/tools/msst-venv/bin/python. Outputs go to ~/ndsp-presets/learn/separator-screen/.

A descriptive screen, not a gate: m_w = log d_w(S) − log d_w(T) (`rank_margin.distance`), with the
reference a stem of a known-target fake recording mixed into the part's real backing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import shutil
import subprocess
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import rank_margin as RM  # noqa: E402  (stdlib-only at import)

SR = 48000
CROP = 480_000
LATENCY = 52
AMPS = ("pr12", "sw50r")
# slug -> (band, gain class, C′ fold under docs/song-settings-folds.json)
PARTS = {
    "cambridge-colour-me-red-elecgtr01": ("Diesel13", "crunch", 1),
    "cambridge-femme-elecgtr3": ("Wall Of Death", "crunch", 0),
    "cambridge-get-out-of-bed-elecgtr1": ("Magician's Nephew", "crunch", 1),
    "cambridge-just-don-t-talk-elecgtr3": ("Timo And The Timezone", "clean", 3),
    "cambridge-magilla-elecgtr1dt": ("Turbosauro", "clean", 2),
}
LOUD = ("cambridge-get-out-of-bed-elecgtr1", "cambridge-just-don-t-talk-elecgtr3")   # other guitars > 0 dB
ROWS = ("htdemucs", "mega53", "blend")
ELIGIBLE = ("mega53", "blend")
REBUILT_ROWS = ("clean", *ROWS)            # m_both rows
CAP = 170                                  # hard stop on all renders (plan, budget)
FAKE_RENDERS = 2                           # warm-up S, T on the 30-s DI
CELL_RENDERS = 12                          # warm-up, S and T through 5 DIs, the repeat S
INFORMATIVE_GAP = 0.1
COH_MARGIN = 0.02
LAG_TOL = 3
REPEAT_TOL = 0.005
STEM_REPEAT_TOL = 1e-5
LINEUP_TOL = 1e-6
CROSSOVER_HZ, CROSSOVER_ORDER = 6000.0, 4
THREADS = 4
P1 = "Guitar-TECHS P1"
MSST_COMMIT = "ea7eb9c20ea0e3f94368a30fc1654b51cdd55789"
STEM = "electric-guitar"
SWAP_GROWTH_MB = 256.0


def home():
    return pathlib.Path("~/ndsp-presets").expanduser()


def out_dir():
    return home() / "learn/separator-screen"


def work3():
    return home() / "learn/set3/stems/_work"


def msst_root():
    return home() / "tools/msst"


def cell_key(slug, amp):
    return f"{slug}|{amp}"


def cells():
    return [(s, a) for s in sorted(PARTS) for a in AMPS]


def _atomic(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    tmp.replace(path)


def _sha_file(path, block=1 << 24):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(block):
            h.update(chunk)
    return h.hexdigest()


def _sha(a):
    return hashlib.sha256(a.tobytes()).hexdigest()


# --- parts and leaks ----------------------------------------------------------------------------

def check_parts():
    """The 5 are `cprime_folds.check`'s selection and knob ceiling's parts, with the declared
    class; their folds are song-settings' ones."""
    from learn import knob_ceiling as K
    from learn import set3
    from learn import song_settings as SS

    man = json.loads((home() / "learn/set3/stems/manifest.json").read_text())["parts"]
    ps = {p["slug"]: p for p in set3.parts("development")}
    check = sorted(s for s, v in man.items() if v.get("usable") and ps[s]["gain_class"] in ("clean", "crunch"))
    assert check == sorted(PARTS), check
    kp, fo = K.parts(), SS.folds()
    for s, (band, cls, f) in PARTS.items():
        assert s in kp and kp[s]["gain_class"] == cls and kp[s]["band"] == band, s
        assert fo[band] == f, (s, fo[band])
        assert man[s]["multi_guitar_mix"], s


def trained_bands(fold, k3_fold_of, cache_bands):
    """The bands fold f's C′ trained on: every cache band outside fold f under K3, plus P1."""
    return {b for b in cache_bands if k3_fold_of.get(b, -1) != fold} | {P1}


def leaks(band, fold, k3_fold_of, cache_bands):
    return band in trained_bands(fold, k3_fold_of, cache_bands)


def assert_leak_free(slug):
    from learn import train as TR

    band, _, f = PARTS[slug]
    k3, _ = TR.k3_folds()
    cb = RM._cache_bands(("cache", "cache-sw50r", "cache-ac20"))
    assert cb, "no cache meta.json found"
    assert not leaks(band, f, k3, cb), (slug, band, f)


# --- the 30-s pieces ----------------------------------------------------------------------------

def window(slug):
    return json.loads((work3() / "contexts.json").read_text())[slug]


def _record(slug):
    from learn import set3

    return json.loads((set3.SET3_CROPS / slug / "record.json").read_text())


def _session_track(rec, path, name, cs, ce):
    import numpy as np

    from analysis import io
    from learn import set3

    audio = io.load(set3.SET3_ROOT / path / name)
    assert audio.sha256 == rec["verified_source_sha256"][name], name
    n = rec["session_frames"]
    x = np.zeros(n, np.float32)
    m = audio.mono().astype(np.float32)[:n]
    x[:len(m)] = m
    return x[cs:ce].astype(np.float64)


def _crop_read(slug, name):
    from learn import confirm_run as CR
    from learn import set3

    return CR.mono(set3.SET3_CROPS / slug / name)


def lineup(a, b, what):
    import numpy as np

    d = float(np.max(np.abs(np.asarray(a, np.float64) - np.asarray(b, np.float64))))
    if d >= LINEUP_TOL:
        raise SystemExit(f"line-up check failed: {what}: max |difference| {d:.3g}")
    return d


def build_context(slug):
    """inst, backing (inst − own amp tracks), solo backing (also − other guitar tracks), the raw
    DI over the window scaled by the crop's −22.9 LUFS gain, and the line-up checks."""
    import numpy as np
    import soundfile as sf

    w, rec = window(slug), _record(slug)
    cs, ce, off = w["context_start_frame"], w["context_end_frame"], w["crop_offset_in_context"]
    vocals, own = set(rec["vocal_tracks"]), set(w["own_amp_tracks"])
    others = set(w["other_guitar_tracks_in_mix"])
    inst = np.zeros(ce - cs)
    own_x, oth_x = np.zeros(ce - cs), np.zeros(ce - cs)
    for name in rec["included_mix_tracks"]:
        if name in vocals:
            continue
        x = _session_track(rec, w["session_path"], name, cs, ce)
        inst += x
        if name in own:
            own_x += x
        if name in others:
            oth_x += x
    stored, _ = sf.read(str(work3() / "contexts" / slug / "mix_instrumental.wav"), dtype="float32")
    checks = {"context": lineup(inst.astype(np.float32), stored, f"{slug} context")}
    backing = inst - own_x
    bname = "backing_instrumental.wav" if vocals else "backing.wav"
    checks["backing"] = lineup(backing[off:off + CROP], _crop_read(slug, bname), f"{slug} {bname}")
    di = _session_track(rec, w["session_path"], rec["pairing"]["di"], cs, ce)
    crop_di = _crop_read(slug, "di.wav")
    checks["di"] = lineup(di[off:off + CROP], crop_di, f"{slug} di.wav")
    g = di_gain(crop_di)
    return {"inst": inst, "backing": backing, "solo_backing": backing - oth_x, "di": di * g,
            "offset": off, "di_gain": g, "checks": checks, "others": sorted(others)}


def loudness(x):
    import numpy as np
    import pyloudnorm

    return float(pyloudnorm.Meter(SR).integrated_loudness(np.asarray(x, np.float64)))


def di_gain(crop_di, target_lufs=-22.9):
    """The gain `direc_check.to_lufs` applies to the crop's DI."""
    return 10 ** ((target_lufs - loudness(crop_di)) / 20)


def fake_gain(render_crop, reference):
    """The one gain that puts the render's crop at the reference's integrated loudness."""
    return 10 ** ((loudness(reference) - loudness(render_crop)) / 20)


def target(K, amp, S):
    """The control's target, exactly as `song_settings.control_render` builds it."""
    dims = K.space(amp, S)
    t = K.perturbed(dims, S, {**K.PERTURB[amp], **K.PERTURB_ALL})
    mic = ("cabParameters", K.CONTROL_MIC[amp])
    t[mic] = str((int(S[mic]) + 4) % 10)
    return t


# --- separators ---------------------------------------------------------------------------------

def to44(x):
    from scipy.signal import resample_poly

    return resample_poly(x, 147, 160)


def to48(y, n):
    import numpy as np
    from scipy.signal import resample_poly

    z = resample_poly(y, 160, 147)
    out = np.zeros(n, np.float32)
    k = min(n, len(z))
    out[:k] = z[:k]
    return out


def verify_msst(root=None):
    """The provenance hashes and the repo commit; returns provenance.json."""
    root = pathlib.Path(root or msst_root())
    prov = json.loads((root / "provenance.json").read_text())
    for f in prov["files"]:
        got = _sha_file(root / f["path"])
        if got != f["sha256"]:
            raise SystemExit(f"hash mismatch: {f['path']}: {got}")
    head = root / "repo" / ".git"
    if head.exists():
        c = subprocess.run(["git", "-C", str(root / "repo"), "rev-parse", "HEAD"], capture_output=True, text=True)
        if c.stdout.strip() != prov["commit"] or prov["commit"] != MSST_COMMIT:
            raise SystemExit(f"MSST repo not at {MSST_COMMIT}: {c.stdout.strip()}")
    return prov


def prune_heads(model, config, keep):
    """Keep only the mask estimators of the stems in `keep` (in that order), and relabel."""
    names = list(config.training.instruments)
    idx = [names.index(k) for k in keep]
    heads = model.mask_estimators
    model.mask_estimators = type(heads)([heads[i] for i in idx])
    model.num_stems = len(idx)
    config.training.instruments = list(keep)
    return model, config


def peak_rss_mb():
    import resource

    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / 1e6 if sys.platform == "darwin" else r / 1e3


def swap_used_mb():
    try:
        s = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True).stdout
        used = s.split("used =")[1].split()[0]
        return float(used.rstrip("M"))
    except Exception:
        return None


class MsstSeparator:
    """Mega-53's electric-guitar head on the CPU (the msst-venv)."""

    def __init__(self, prune=True, root=None):
        import torch
        import yaml

        os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "0"
        torch.set_num_threads(THREADS)
        self.root = pathlib.Path(root or msst_root())
        self.prov = verify_msst(self.root)
        sys.path.insert(0, str(self.root / "repo"))
        from ml_collections import ConfigDict
        from models.bs_roformer.bs_roformer import BSRoformer

        files = {pathlib.Path(f["path"]).suffix: self.root / f["path"] for f in self.prov["files"]}
        with open(files[".yaml"]) as f:
            self.config = ConfigDict(yaml.load(f, Loader=yaml.FullLoader))
        self.model = BSRoformer(**dict(self.config.model))
        state = torch.load(files[".ckpt"], map_location="cpu")
        state = state.get("state_dict", state) if isinstance(state, dict) else state
        self.model.load_state_dict(state)
        self.pruned = prune
        if prune:
            prune_heads(self.model, self.config, [STEM])
        self.model = self.model.eval().to("cpu")
        self.device = torch.device("cpu")
        self.swap0 = swap_used_mb()

    def __call__(self, x):
        """The electric-guitar stem of mono 48-kHz `x`, at 48 kHz, the same length."""
        import numpy as np
        from utils.model_utils import demix

        y = to44(np.asarray(x, np.float64)).astype(np.float32)
        out = demix(self.config, self.model, np.stack([y, y]), self.device, "bs_roformer", pbar=False)
        stem = out[STEM].mean(0)
        s = swap_used_mb()
        if self.swap0 is not None and s is not None and s - self.swap0 > SWAP_GROWTH_MB:
            raise SystemExit(f"swap grew by {s - self.swap0:.0f} MB: stopping Mega-53")
        return to48(stem, len(x))

    def info(self):
        import torch

        freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout
        return {"model": "mega53", "stem": STEM, "pruned": self.pruned, "provenance": self.prov,
                "torch_version": torch.__version__, "threads": THREADS, "device": "cpu",
                "inference": dict(self.config.inference), "peak_rss_mb": round(peak_rss_mb(), 1),
                "swap_used_mb": swap_used_mb(), "pip_freeze": freeze.splitlines()}


def htdemucs():
    """`learn.separate.GuitarSeparator` on the CPU, then 4 threads (as the stored set-3 stems)."""
    import torch

    os.environ["DEVICE"] = "cpu"
    from learn.separate import GuitarSeparator

    sep = GuitarSeparator()
    torch.set_num_threads(THREADS)
    assert sep.device == "cpu"
    return sep


# --- the blend ----------------------------------------------------------------------------------

def crossover_sos():
    from scipy.signal import butter

    return butter(CROSSOVER_ORDER, CROSSOVER_HZ, "low", fs=SR, output="sos")


def lowpass(x):
    from scipy.signal import sosfiltfilt

    return sosfiltfilt(crossover_sos(), x)


def blend(mega, hd):
    """LP(mega53) + (htdemucs − LP(htdemucs)): exactly complementary, zero phase."""
    import numpy as np

    mega, hd = np.asarray(mega, np.float64), np.asarray(hd, np.float64)
    return lowpass(mega) + (hd - lowpass(hd))


def blend_lag(mega, hd):
    return RM.gcc_lag(mega, hd)


# --- stem metrics against the clean fake --------------------------------------------------------

def env_variation_err(stem, fake):
    """std of the 10-ms log-RMS frames (within 40 dB of the fake's loudest): stem − fake, dB."""
    ef, es = RM._frames_db(fake), RM._frames_db(stem)
    k = min(len(ef), len(es))
    ef, es = ef[:k], es[:k]
    sel = ef >= ef.max() - 40
    return float(es[sel].std() - ef[sel].std())


def onsets(fake, hop=256, min_gap_s=0.05):
    """Sample positions of the fake's spectral-flux peaks above median + 3 × MAD."""
    import numpy as np

    f = RM._flux(np.asarray(fake, np.float64))
    med = np.median(f)
    thr = med + 3 * np.median(np.abs(f - med))
    gap = int(math.ceil(min_gap_s * SR / hop))
    out, last = [], -gap
    for k in range(1, len(f) - 1):
        if f[k] > thr and f[k] >= f[k - 1] and f[k] >= f[k + 1] and k - last >= gap:
            out.append((k + 1) * hop)
            last = k
    return out


def _slopes(x, ts):
    """Per onset: the rise of the 1-ms RMS envelope from 5 ms before it to its peak within 30 ms,
    as a fraction of that peak, per ms of rise time (level-free, so a quieter floor can't steepen it)."""
    import numpy as np

    e = RM.envelope(x, 1.0)
    pre, post = int(0.005 * SR), int(0.030 * SR)
    out = []
    for t in ts:
        a, b = t - pre, min(len(e), t + post)
        if a < 0 or b <= t:
            out.append(None)
            continue
        p = t + int(np.argmax(e[t:b]))
        out.append((e[p] - e[a]) / (e[p] + 1e-12) / ((p - a) / SR * 1000))
    return out


def attack_slope_err(stem, fake):
    """Median over the fake's onsets of log2(slope_stem / slope_fake); negative = blunted."""
    import numpy as np

    ts = onsets(fake)
    sf_, ss = _slopes(np.asarray(fake, np.float64), ts), _slopes(np.asarray(stem, np.float64), ts)
    r = [math.log2(max(s, 1e-3) / f) for f, s in zip(sf_, ss) if f is not None and s is not None and f > 0]
    return float(np.median(r)) if r else None


def si_sdr(est, ref):
    import numpy as np

    est, ref = np.asarray(est, np.float64), np.asarray(ref, np.float64)
    a = np.dot(est, ref) / (np.dot(ref, ref) + 1e-20)
    t = a * ref
    return float(10 * np.log10(np.sum(t ** 2) / (np.sum((est - t) ** 2) + 1e-20) + 1e-20))


THIRD_OCTAVES = [1000 * 2 ** (k / 3) for k in range(-14, 13)]      # 27 bands, 40 Hz–16 kHz


def edge_bands(stem, fake):
    """1/3-octave level of stem − fake (Welch 8192), minus the mean over the 27 bands, at the
    bands centred near 63 Hz, 8 kHz and 12.7 kHz."""
    import numpy as np
    from scipy.signal import welch

    f, ps = welch(stem, fs=SR, nperseg=8192)
    _, pf = welch(fake, fs=SR, nperseg=8192)
    d = []
    for c in THIRD_OCTAVES:
        m = (f >= c * 2 ** (-1 / 6)) & (f < c * 2 ** (1 / 6))
        d.append(10 * np.log10((ps[m].sum() + 1e-30) / (pf[m].sum() + 1e-30)))
    d = np.array(d) - np.mean(d)
    pick = {"63": 63.0, "8k": 8000.0, "12.7k": 12700.0}
    return {k: float(d[int(np.argmin([abs(math.log(c / v)) for c in THIRD_OCTAVES]))]) for k, v in pick.items()}


def stem_metrics(stem, fake):
    return {"crest_err": RM.crest_db(stem) - RM.crest_db(fake), "env_var_err": env_variation_err(stem, fake),
            "attack_slope_err": attack_slope_err(stem, fake), "si_sdr": si_sdr(stem, fake),
            "edge": edge_bands(stem, fake)}


# --- decisions ----------------------------------------------------------------------------------

def _pos(v):
    return v is not None and v > 0


def informative_from(d):
    """d: cell -> {'S': d_S, 'T': d_T} (full window, measure DI, clean fake)."""
    return sorted(c for c, x in d.items() if x["S"] is not None and x["T"] is not None
                  and x["S"] - x["T"] >= INFORMATIVE_GAP)


def screen(m_sep, coh, inf, hd_lag_fail=False):
    """m_sep: row -> cell -> m (None = refusal or stopped); coh: row -> mean real-song coherence.
    Per eligible row: advance iff more positives than htdemucs, no flip, coherence within 0.02."""
    n = len(inf)
    if n < 4 or hd_lag_fail:
        return {"n": n, "verdict": "undecided", "rows": {}}
    hd = {c for c in inf if _pos(m_sep["htdemucs"].get(c))}
    out = {"n": n, "htdemucs_positive": len(hd), "ceiling": len(hd) == n, "rows": {}}
    for r in ELIGIBLE:
        pos = {c for c in inf if _pos(m_sep.get(r, {}).get(c))}
        flips = sorted(hd - pos)
        c_hd, c_r = coh.get("htdemucs"), coh.get(r)
        coh_ok = c_hd is not None and c_r is not None and c_r >= c_hd - COH_MARGIN
        more = len(pos) > len(hd)
        out["rows"][r] = {"positive": len(pos), "more": more, "flips": flips, "coherence_ok": coh_ok,
                          "advances": more and not flips and coh_ok}
    out["verdict"] = "screened"
    return out


def reading(m_hd, inf, hd_lag_fail=False):
    """On htdemucs: ≤ 1 inversion -> separation isn't what breaks it; ≥ ceil(n/3) -> co-equal;
    else partial; n < 4 -> undecided."""
    n = len(inf)
    if n < 4 or hd_lag_fail:
        return {"n": n, "inversions": None, "reading": "undecided"}
    inv = sum(not _pos(m_hd.get(c)) for c in inf)
    if inv <= 1:
        r = "not-separation"
    elif inv >= math.ceil(n / 3):
        r = "co-equal"
    else:
        r = "partial"
    return {"n": n, "inversions": inv, "reading": r}


def leave_one_part_out(m_sep, coh_parts, inf, hd_lag_fail=False):
    """Screen and reading with each part's cells dropped; coherence over the other 4 parts."""
    import statistics

    out = {}
    for p in sorted(PARTS):
        keep = [c for c in inf if not c.startswith(p + "|")]
        coh = {r: (statistics.fmean(v for s, v in coh_parts[r].items() if s != p)
                   if r in coh_parts and all(v is not None for v in coh_parts[r].values()) else None)
               for r in ROWS}
        out[p] = {"screen": screen(m_sep, coh, keep, hd_lag_fail),
                  "reading": reading(m_sep["htdemucs"], keep, hd_lag_fail)}
    return out


def _summary(sc, rd):
    return ({r: v["advances"] for r, v in sc.get("rows", {}).items()} or sc["verdict"], rd["reading"])


def fragility(primary, others):
    """Names of the readings (windows, masks, parts left out) that change the declared verdicts."""
    p = _summary(*primary)
    return sorted(k for k, (sc, rd) in others.items() if _summary(sc, rd) != p)


# --- render accounting --------------------------------------------------------------------------

def renders_on_disk():
    d = out_dir()
    n = 0
    for p in list((d / "fakes").glob("*.json")) + list((d / "scores").glob("*.json")):
        n += json.loads(p.read_text()).get("renders", 0)
    return n


def cap_ok(on_disk, need):
    return on_disk + need <= CAP


def render_running():
    return subprocess.run(["pgrep", "-f", "au_render_server"], capture_output=True).returncode == 0


def disk_ok():
    return shutil.disk_usage(pathlib.Path.home()).free / 1e9 >= RM.MIN_FREE_GB


# --- steps --------------------------------------------------------------------------------------

def step_contexts():
    import numpy as np

    check_parts()
    log = {}
    for slug in sorted(PARTS):
        assert_leak_free(slug)
        c = build_context(slug)
        d = out_dir() / "contexts" / slug
        d.mkdir(parents=True, exist_ok=True)
        for k in ("inst", "backing", "solo_backing", "di"):
            np.save(d / f"{k}.npy", c[k].astype(np.float32))
        log[slug] = {"offset": c["offset"], "di_gain": c["di_gain"], "checks": c["checks"],
                     "other_guitar_tracks": c["others"]}
        print(slug, c["checks"], flush=True)
    _atomic(out_dir() / "contexts.json", log)


def step_fakes():
    import numpy as np

    from learn import knob_ceiling as K

    rr = K.Renderer()                                       # isolate=True
    try:
        menu = rr.menu()
        for slug, amp in cells():
            f = out_dir() / "fakes" / f"{slug}-{amp}.json"
            if f.exists():
                continue
            if not disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            if not cap_ok(renders_on_disk(), FAKE_RENDERS):
                raise SystemExit(f"render cap {CAP} reached")
            cd = out_dir() / "contexts" / slug
            di, backing = np.load(cd / "di.npy"), np.load(cd / "backing.npy").astype(np.float64)
            solo = np.load(cd / "solo_backing.npy").astype(np.float64)
            off = json.loads((out_dir() / "contexts.json").read_text())[slug]["offset"]
            sel, S = menu[amp][K.START[PARTS[slug][1]][amp]]
            T = target(K, amp, S)
            rr.render(di, sel, S)                           # warm-up
            y = np.asarray(rr.render(di, sel, T), np.float64)
            y = y.mean(axis=1) if y.ndim == 2 else y
            g = fake_gain(y[off:off + CROP], _crop_read(slug, "reference.wav"))
            fake = y * g
            d = out_dir() / "fakes" / f"{slug}-{amp}"
            d.mkdir(parents=True, exist_ok=True)
            np.save(d / "fake30.npy", fake.astype(np.float32))
            np.save(d / "clean.npy", fake[off:off + CROP])
            np.save(d / "mix.npy", (backing + fake).astype(np.float32))
            np.save(d / "solo_mix.npy", (solo + fake).astype(np.float32))
            (d / "target.json").write_text(json.dumps({f"{m}/{k}": v for (m, k), v in T.items()}))
            _atomic(f, {"cell": cell_key(slug, amp), "renders": FAKE_RENDERS, "gain": g,
                        "fake_sha256": _sha(fake.astype(np.float32))})
            print(slug, amp, round(g, 4), rr.count, flush=True)
    finally:
        rr.close()


def _inputs():
    """name -> (30-s input path, crop offset): 10 mixes, 10 solo mixes, 5 real contexts."""
    ctx = json.loads((out_dir() / "contexts.json").read_text())
    out = {}
    for slug, amp in cells():
        d = out_dir() / "fakes" / f"{slug}-{amp}"
        out[f"{slug}-{amp}"] = (d / "mix.npy", ctx[slug]["offset"])
        out[f"{slug}-{amp}-solo"] = (d / "solo_mix.npy", ctx[slug]["offset"])
    for slug in PARTS:
        out[f"{slug}-real"] = (out_dir() / "contexts" / slug / "inst.npy", ctx[slug]["offset"])
    return out


def step_separate(row):
    import time

    import numpy as np

    if render_running():
        raise SystemExit("a Morgan render process is running: separation waits for an idle renderer")
    if row == "mega53":
        ident = json.loads((out_dir() / "identity.json").read_text())
        sep = MsstSeparator(prune=ident["identical"])
    else:
        sep = htdemucs()
    d = out_dir() / "stems" / row
    d.mkdir(parents=True, exist_ok=True)
    log = {}
    for name, (path, off) in _inputs().items():
        if (d / f"{name}.npy").exists():
            continue
        x = np.load(path).astype(np.float32)
        t = time.time()
        y = np.asarray(sep(x), np.float32)
        assert len(y) == len(x)
        if row == "htdemucs" and name.endswith("-real"):
            stored = stored_htdemucs(name[:-5])
            dev = float(np.max(np.abs(y[off:off + CROP] - stored)))
            if dev > STEM_REPEAT_TOL:
                raise SystemExit(f"htdemucs repeat check failed: {name}: {dev:.3g}")
            log.setdefault("repeat", {})[name] = dev
        np.save(d / f"{name}.npy", y)
        log[name] = {"wall_s": round(time.time() - t, 1), "peak_rss_mb": round(peak_rss_mb(), 1)}
        print(row, name, log[name], flush=True)
    info = sep.info() if hasattr(sep, "info") else {}
    old = json.loads((d / "run.json").read_text()) if (d / "run.json").exists() else {}
    old.update(info, threads=THREADS)
    old.setdefault("runs", {}).update(log)
    _atomic(d / "run.json", old)


def stored_htdemucs(slug):
    """The stored set-3 stem (`_work/separate_demucs.py`, CPU, 4 threads), the 10-s crop."""
    import soundfile as sf

    x, sr = sf.read(str(home() / "learn/set3/stems/htdemucs_6s" / slug / "instrumental_guitar.wav"),
                    dtype="float32")
    assert sr == SR and x.ndim == 1
    return x


def step_identity():
    """Pruned against full Mega-53 on colour-me-red's real context (max |difference| 0.0)."""
    import numpy as np

    if render_running():
        raise SystemExit("a Morgan render process is running")
    x = np.load(out_dir() / "contexts" / "cambridge-colour-me-red-elecgtr01" / "inst.npy").astype(np.float32)
    full = MsstSeparator(prune=False)(x)
    pruned = MsstSeparator(prune=True)(x)
    dev = float(np.max(np.abs(full - pruned)))
    _atomic(out_dir() / "identity.json", {"max_abs_diff": dev, "identical": dev == 0.0,
                                          "peak_rss_mb": round(peak_rss_mb(), 1)})
    print("pruned vs full: max |difference|", dev, flush=True)


def step_blend():
    """The blends, the relative-lag check, and each stem's lag against the clean fake."""
    import numpy as np

    sd = out_dir() / "stems"
    (sd / "blend").mkdir(parents=True, exist_ok=True)
    log = {}
    for name, (_, off) in _inputs().items():
        m, h = sd / "mega53" / f"{name}.npy", sd / "htdemucs" / f"{name}.npy"
        if not (m.exists() and h.exists()):
            log[name] = {"blend": "stopped: a stem is missing"}
            continue
        mega, hd = np.load(m).astype(np.float64), np.load(h).astype(np.float64)
        rel = blend_lag(mega, hd)
        row = {"relative_lag": rel, "level_4_8k_db": _band_db(mega, hd, 4000, 8000)}
        if rel != 0:
            row["blend"] = "stopped: relative lag"
        else:
            np.save(sd / "blend" / f"{name}.npy", blend(mega, hd).astype(np.float32))
            row["blend"] = "ok"
        if not name.endswith("-real"):
            cell = name[:-5] if name.endswith("-solo") else name
            clean = np.load(out_dir() / "fakes" / cell / "clean.npy")
            for r in ROWS:
                p = sd / r / f"{name}.npy"
                if p.exists():
                    lag = RM.gcc_lag(np.load(p)[off:off + CROP].astype(np.float64), clean)
                    row[f"lag_{r}"] = lag
                    row[f"lag_ok_{r}"] = abs(lag) <= LAG_TOL
        log[name] = row
        print(name, row, flush=True)
    _atomic(out_dir() / "blend.json", log)


def _band_db(a, b, lo, hi):
    import numpy as np
    from scipy.signal import welch

    f, pa = welch(a, fs=SR, nperseg=8192)
    _, pb = welch(b, fs=SR, nperseg=8192)
    m = (f >= lo) & (f < hi)
    return float(10 * np.log10((pa[m].sum() + 1e-30) / (pb[m].sum() + 1e-30)))


def _stem_ok(name, row, lags):
    """A row's stem for this mix exists and passed its lag checks."""
    v = lags.get(name, {})
    if row == "blend":
        return v.get("blend") == "ok" and v.get("lag_ok_blend", True) and v.get("lag_ok_mega53", True)
    return v.get(f"lag_ok_{row}", True) and (out_dir() / "stems" / row / f"{name}.npy").exists()


def step_rebuild():
    """C′ (the part's fold, CPU) rebuilds every 10-s reference: fake cells' clean and stems, and
    the real songs' stems and amp track; re-EQ to fold 2, −22.9 LUFS; lag check vs the raw DI."""
    import numpy as np
    import torch

    from learn import direc as D
    from learn import song_settings as SS
    from learn.direc_check import eq_to, to_lufs

    avg = {f: np.load(SS.MODELS / "cache" / f"average-fold{f}.npy") for f in range(4)}
    lags = json.loads((out_dir() / "blend.json").read_text())
    ctx = json.loads((out_dir() / "contexts.json").read_text())
    rd = out_dir() / "rebuilt"
    rd.mkdir(parents=True, exist_ok=True)
    log = json.loads((rd / "log.json").read_text()) if (rd / "log.json").exists() else {}
    nets = {}
    for slug in sorted(PARTS):
        assert_leak_free(slug)
        f = PARTS[slug][2]
        assert SS.cprime_ready(f), f
        if f not in nets:
            nets[f] = D.load_model(SS.cprime(f)).eval()
        off = ctx[slug]["offset"]
        raw = _crop_read(slug, "di.wav")
        jobs = {}
        for amp in AMPS:
            name = f"{slug}-{amp}"
            jobs[f"{name}/clean"] = np.load(out_dir() / "fakes" / name / "clean.npy")
            for r in ROWS:
                if _stem_ok(name, r, lags):
                    jobs[f"{name}/{r}"] = np.load(out_dir() / "stems" / r / f"{name}.npy")[off:off + CROP]
        for r in ROWS:
            p = out_dir() / "stems" / r / f"{slug}-real.npy"
            if p.exists() and (r != "blend" or lags.get(f"{slug}-real", {}).get("blend") == "ok"):
                jobs[f"{slug}-real/{r}"] = np.load(p)[off:off + CROP]
        jobs[f"{slug}-real/amp"] = _crop_read(slug, "reference.wav")
        for key, x in jobs.items():
            dst = rd / f"{key.replace('/', '__')}.npy"
            if dst.exists():
                continue
            y = D.rebuild(nets[f], np.asarray(x, np.float32), device=torch.device("cpu")).astype(np.float64)
            y = to_lufs(eq_to(y, avg[2] - avg[f]))
            entry = {"fold": f}
            if "-real/" not in key:                         # a rebuild of the fake aligns to the DI
                lag = RM.gcc_lag(y, raw)
                entry.update(lag=lag, lag_ok=abs(lag) <= LAG_TOL)
            np.save(dst, y)
            log[key] = entry
            print(key, entry, flush=True)
    _atomic(rd / "log.json", log)


def _score(ref, ys, yt, masks):
    """mask name -> window -> {S, T, m} (lag 0)."""
    out = {}
    for mn, mask in masks.items():
        out[mn] = {}
        for w in RM.WINDOWS:
            row = {}
            for st, y in (("S", ys), ("T", yt)):
                d, fb, why = RM.distance(ref, y, mask, 0, w)
                row[st] = {"d": d, "fallback": fb, "reason": None if d is not None else why}
            row["m"] = RM.margin(row["S"]["d"], row["T"]["d"])
            out[mn][w] = row
    return out


def step_render():
    import numpy as np

    from learn import knob_ceiling as K

    lags = json.loads((out_dir() / "blend.json").read_text())
    rlog = json.loads((out_dir() / "rebuilt" / "log.json").read_text())
    ctx = json.loads((out_dir() / "contexts.json").read_text())
    ps = K.parts()
    rr = K.Renderer()                                       # isolate=True
    try:
        menu = rr.menu()
        for slug, amp in cells():
            name = f"{slug}-{amp}"
            f = out_dir() / "scores" / f"{name}.json"
            if f.exists():
                continue
            if not disk_ok():
                raise SystemExit("free disk below the 31 GB guard")
            if not cap_ok(renders_on_disk(), CELL_RENDERS):
                raise SystemExit(f"render cap {CAP} reached")
            off = ctx[slug]["offset"]
            sel, S = menu[amp][K.START[PARTS[slug][1]][amp]]
            fd = out_dir() / "fakes" / name
            T = {tuple(k.rsplit("/", 1)): v for k, v in json.loads((fd / "target.json").read_text()).items()}
            clean = np.load(fd / "clean.npy")
            measure = K.measure_di(ps[slug])
            m32 = measure.astype(np.float32)
            n = 0
            rr.render(m32, sel, S)                          # warm-up
            ys, yt = rr.render(m32, sel, S), rr.render(m32, sel, T)
            n += 3
            np.save(fd / "measure-S.npy", np.asarray(ys, np.float32))
            np.save(fd / "measure-T.npy", np.asarray(yt, np.float32))
            refs = {"clean": clean}
            for r in ROWS:
                for suffix in ("", "-solo"):
                    if _stem_ok(name + suffix, r, lags):
                        refs[f"{r}{suffix}"] = np.load(out_dir() / "stems" / r / f"{name}{suffix}.npy")[off:off + CROP]
            res = {"cell": cell_key(slug, amp), "m_sep": {}, "m_both": {}}
            for k, ref in refs.items():                     # the other mask for m_sep: the reference
                res["m_sep"][k] = _score(ref, ys, yt, {"measure": measure, "ref": ref})
            for r in REBUILT_ROWS:
                key = f"{name}/{r}"
                e = rlog.get(key)
                if r not in refs or e is None or not e.get("lag_ok"):
                    res["m_both"][r] = {"stopped": "missing stem or rebuild lag check"}
                    continue
                v = np.load(out_dir() / "rebuilt" / f"{name}__{r}.npy")
                v32 = v.astype(np.float32)
                vs, vt = rr.render(v32, sel, S), rr.render(v32, sel, T)
                n += 2
                res["m_both"][r] = _score(refs[r], vs, vt, {"v": v, "measure": measure})
            y2 = rr.render(m32, sel, S)
            n += 1
            d1 = res["m_sep"]["clean"]["measure"]["full"]["S"]["d"]
            d2, _, _ = RM.distance(clean, y2, measure, 0, "full")
            ok = d1 is not None and d2 is not None and abs(math.log(d2 / d1)) <= REPEAT_TOL
            res.update(renders=n, repeat={"d1": d1, "d2": d2, "ok": ok})
            _atomic(f, res)
            print(name, {k: v["measure"]["full"]["m"] for k, v in res["m_sep"].items()}, rr.count, flush=True)
            if not ok:
                raise SystemExit(f"repeat render failed: {name}: {d1} vs {d2}")
    finally:
        rr.close()


def _m(scores, kind, row, mask, w):
    s = scores.get(kind, {}).get(row)
    if not s or "stopped" in s:
        return None
    return s[mask][w]["m"]


def step_report():
    import statistics

    import numpy as np

    from learn import confirm_run as CR
    from learn import set3
    from learn.residual_eval import _aligned, _coherence

    sc = {cell_key(s, a): json.loads((out_dir() / "scores" / f"{s}-{a}.json").read_text()) for s, a in cells()}
    lags = json.loads((out_dir() / "blend.json").read_text())
    dist = {c: {"S": v["m_sep"]["clean"]["measure"]["full"]["S"]["d"],
                "T": v["m_sep"]["clean"]["measure"]["full"]["T"]["d"]} for c, v in sc.items()}
    inf = informative_from(dist)
    hd_fail = any(not lags.get(c.replace("|", "-"), {}).get("lag_ok_htdemucs", True) for c in inf)

    def msep(w="full", mask="measure", solo=False):
        sfx = "-solo" if solo else ""
        return {r: {c: _m(v, "m_sep", r + sfx, mask, w) for c, v in sc.items()} for r in ROWS} | \
               {"clean": {c: _m(v, "m_sep", "clean", mask, w) for c, v in sc.items()}}

    # real-song coherence (check 2's measure, the part's fold C′) and on the fake cells
    ps3 = {p["slug"]: p for p in set3.parts("development")}
    rd = out_dir() / "rebuilt"
    coh_parts = {r: {} for r in (*ROWS, "amp")}
    for slug in sorted(PARTS):
        di = _crop_read(slug, "di.wav")
        for r in coh_parts:
            p = rd / f"{slug}-real__{r}.npy"
            if p.exists():
                a, b, _ = _aligned(np.load(p), di, ps3[slug]["judge_lag_samples"] + LATENCY)
                coh_parts[r][slug] = _coherence(a, b)[1]
            else:
                coh_parts[r][slug] = None
    coh = {r: (statistics.fmean(v.values()) if all(x is not None for x in v.values()) else None)
           for r, v in coh_parts.items()}
    coh_fake = {}
    for c in sc:
        name = c.replace("|", "-")
        di = _crop_read(c.split("|")[0], "di.wav")
        for r in REBUILT_ROWS:
            p = rd / f"{name}__{r}.npy"
            if p.exists():
                a, b, _ = _aligned(np.load(p), di, 0)
                coh_fake.setdefault(r, {})[c] = _coherence(a, b)[1]

    primary_m = msep()
    primary = (screen(primary_m, coh, inf, hd_fail), reading(primary_m["htdemucs"], inf, hd_fail))
    others = {}
    for w in ("A", "B"):
        m = msep(w)
        others[f"window {w}"] = (screen(m, coh, inf, hd_fail), reading(m["htdemucs"], inf, hd_fail))
    m = msep(mask="ref")
    others["other mask"] = (screen(m, coh, inf, hd_fail), reading(m["htdemucs"], inf, hd_fail))
    lopo = leave_one_part_out(primary_m, {r: coh_parts[r] for r in ROWS}, inf, hd_fail)
    for p, v in lopo.items():
        others[f"without {p}"] = (v["screen"], v["reading"])

    # descriptive: Δm_sep, m_both, the single-guitar variant, stem metrics, the control repeat
    delta = {r: {c: (primary_m[r][c] - primary_m["htdemucs"][c]
                     if primary_m[r][c] is not None and primary_m["htdemucs"][c] is not None else None)
                 for c in sc} for r in ELIGIBLE}
    m_both = {r: {c: _m(v, "m_both", r, "v", "full") for c, v in sc.items()} for r in REBUILT_ROWS}
    solo = msep(solo=True)
    metrics = {}
    for slug, amp in cells():
        name = f"{slug}-{amp}"
        off = json.loads((out_dir() / "contexts.json").read_text())[slug]["offset"]
        clean = np.load(out_dir() / "fakes" / name / "clean.npy")
        for r in ROWS:
            for sfx in ("", "-solo"):
                p = out_dir() / "stems" / r / f"{name}{sfx}.npy"
                if p.exists():
                    metrics.setdefault(r + sfx, {})[cell_key(slug, amp)] = stem_metrics(np.load(p)[off:off + CROP], clean)
    ctl = home() / "learn/song-settings/armA-control"
    repeat = {}
    for slug, amp in cells():
        p = ctl / f"{slug}-{amp}-fake.npy"
        if p.exists():
            ours = np.load(out_dir() / "fakes" / f"{slug}-{amp}" / "clean.npy")
            d, _, _ = RM.distance(np.load(p), ours, K_measure(slug), 0, "full")
            repeat[cell_key(slug, amp)] = d
    snr = {}
    for slug in PARTS:
        p = out_dir() / "stems" / "mega53" / f"{slug}-real.npy"
        if p.exists():
            off = json.loads((out_dir() / "contexts.json").read_text())[slug]["offset"]
            s, r = np.load(p)[off:off + CROP].astype(np.float64), CR.mono(set3.SET3_CROPS / slug / "reference.wav")
            a = np.dot(s, r) / (np.dot(s, s) + 1e-20)
            snr[slug] = float(10 * np.log10(np.sum(r ** 2) / (np.sum((r - a * s) ** 2) + 1e-20)))
    rep = {"informative": inf, "htdemucs_lag_failure": hd_fail,
           "screen": primary[0], "reading": primary[1], "fragile_under": fragility(primary, others),
           "others": {k: {"screen": a, "reading": b} for k, (a, b) in others.items()},
           "m_sep": primary_m, "delta_m_sep": delta, "m_both": m_both,
           "single_guitar": {"m_sep": solo, "reading": reading(solo["htdemucs"], inf),
                             "positive": {r: sum(_pos(solo[r].get(c)) for c in inf) for r in ROWS}},
           "coherence_real": {"mean": coh, "per_part": coh_parts}, "coherence_fake": coh_fake,
           "stem_metrics": metrics, "loud_parts": list(LOUD), "control_fake_repeat": repeat,
           "mega53_real_snr_db": snr, "renders": renders_on_disk()}
    _atomic(out_dir() / "report.json", rep)
    print("informative", len(inf), "| screen", primary[0], "| reading", primary[1],
          "| fragile under", rep["fragile_under"], flush=True)


def K_measure(slug):
    from learn import knob_ceiling as K

    return K.measure_di(K.parts()[slug])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=("contexts", "fakes", "separate", "identity", "blend", "rebuild", "render",
                                     "report"))
    ap.add_argument("--row", choices=("htdemucs", "mega53"))
    a = ap.parse_args(argv)
    if a.step == "separate" and not a.row:
        ap.error("separate needs --row")
    {"contexts": step_contexts, "fakes": step_fakes, "separate": lambda: step_separate(a.row),
     "identity": step_identity, "blend": step_blend, "rebuild": step_rebuild, "render": step_render,
     "report": step_report}[a.step]()


if __name__ == "__main__":
    main()
