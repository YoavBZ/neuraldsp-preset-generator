"""Better target-guitar separation, Step 0 (docs/separation-finetune-plan.md): where the gap is,
and the free fixes. Zero renders, zero training, CPU only, no new separation.

    .venv/bin/python -m learn.separation_ceiling table      # the track table (docs/separation-track-table.json)
    .venv/bin/python -m learn.separation_ceiling measure    # per-part signals and measures; G crops for Step 1
    .venv/bin/python -m learn.separation_ceiling report     # the declared readings R0a, R0b, R0c and YT − M

Stage F's 21 parts, the 10-s crop inside the stored 30-s context, against `reference.wav`. The
stored Mega-53 and htdemucs stems (`arm_a_mega53.fdir("sep", ...)`), and track sums built exactly
as `learn.separate.context` builds the mix (each crop record's `included_mix_tracks`, unity, mono
channel mean, `analysis.io.load`). Outputs go to ~/ndsp-presets/learn/separation-finetune/.

Signals: M, H (stored stems); G (every electric-guitar track in the context: the target, its mics
and doubles included); G_noDT (G without the other guitars' double-tracks); G_mic (the target's own
mic group as it is in the mix); T1, T2 (single-target Wiener on the mix from Mega-53, STFT
2048/512, one and two passes); T3 (0.5·M + 0.5·H, each gain-fitted to the mix); T4
(`separator_screen.blend`). Measures as in the stereo check: gain-fitted SNR, SI-SDR, 1/3-octave
LSD, the 3–10 kHz brightness difference. I: other-electric-guitar energy over the target's in the
crop. X: the share of the session's target-active 10-s sections where the other electric guitars
sit 10 dB or more below the target.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import statistics
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
OUT = HOME / "learn/separation-finetune"
TABLE = PLUGIN_ROOT / "docs/separation-track-table.json"
SR = 48000
CROP = 480_000
SEED = 20261019
N_BOOT = 4000
NFFT, HOP = 2048, 512
SECTION_S = 10
ACTIVE_DBFS = -40.0                      # a section counts for X when the target's RMS reaches this
EXPOSED_DB = -10.0                       # X: other guitars at least 10 dB below the target
HOLM_ALPHA = 0.10
LSD_COST_DB = 1.0
GATE_POINT_DB, GATE_LO_DB = 2.0, 1.0     # Step 3's rule for going straight to the render test
T_ORDER = ("T1", "T2", "T3", "T4")
SIGNALS = ("M", "H", "G", "G_noDT", "G_mic", *T_ORDER)

# --- the track table ----------------------------------------------------------------------------------

F_CLASSES = ("target", "target_other_mic", "double_track_of_target", "double_track_of_other",
             "other_electric_guitar", "rest")
EG = re.compile(r"elec\s*gtr|^gtr\b", re.I)                    # electric-guitar amp tracks by name
NOT_EG = re.compile(r"\bdi\b|di\.wav$|_di\b|\bdi_|keys|vox|acoustic|pre rec|pre record", re.I)
DT = re.compile(r"dt", re.I)
GTR_ID = re.compile(r"(?:elecgtr|gtr)\s*0*(\d+)", re.I)
# Ambiguous names go to rest (the plan): keys through an amp, Eggy's VOX GTR, Quicksand's Intro mics.
AMBIGUOUS = re.compile(r"gtr keys amp|vox gtr|intro(close|far)", re.I)
DROPPED = re.compile(r"pre rec|pre record|band click|rr master", re.I)   # bounces, click, master: dropped
IN_SCOPE_TRAIN = ("Adam Buckley", "Ale Lak", "Starnes And Shah", "Eggy", "John Morgan Kimock", "Swatkins",
                  "The Long Wait")
HIGH_GAIN_TRAIN = ("Death Of A Romantic", "Hollow Ground", "Rebuild The Evil", "Renesans", "Cnoc An Tursa",
                   "Storm Of Particles")


def base(name):
    return name.split("/")[-1]


def is_electric(name):
    b = base(name)
    return bool(EG.search(b)) and not NOT_EG.search(b) and not AMBIGUOUS.search(b)


def gtr_id(name):
    m = GTR_ID.search(base(name))
    return m.group(1) if m else None


def classify_f(name, reference, alternates):
    """A stage-F track's class against its part (the plan's five, doubles split by whose)."""
    if name == reference:
        return "target"
    if name in alternates:
        return "target_other_mic"
    if not is_electric(name):
        return "rest"
    if DT.search(base(name).replace(".wav", "")):
        same = gtr_id(name) is not None and gtr_id(name) == gtr_id(reference)
        return "double_track_of_target" if same else "double_track_of_other"
    return "other_electric_guitar"


def classify_train(name, is_di):
    """A training session's track: electric_guitar (the class target), di (excluded), dropped
    (pre-recorded bounces, click and master files: dropped from both mix and target until listened
    to), rest."""
    if is_di:
        return "di"
    if DROPPED.search(base(name)):
        return "dropped"
    if re.search(r"(^|[_\s\d])di([_\s.]|$)|DI\.wav$|_DI\.wav$|D\.wav$", base(name)) and EG.search(base(name)):
        return "di"
    return "electric_guitar" if is_electric(name) else "rest"


def _catalogs():
    cat12 = json.loads((PLUGIN_ROOT / "docs/validation-datasets.json").read_text())
    cat3 = json.loads((PLUGIN_ROOT / "docs/validation-set3.json").read_text())
    return cat12, cat3


def f_reference(slug, rec, cat12):
    """(reference track, alternates) of a stage-F part, from its declaration."""
    from learn import arm_a_mega53 as A

    part = A.f_part(slug)
    if part["set"] == 12:
        s = [x for x in cat12["sessions"] if x["source"] == rec["source"] and x["song"] == rec["song"]][0]
        p = [q for q in s["parts"] if q["part"] == rec["part"]][0]
        return p["reference"], list(p.get("alternate", []))
    ref = rec["pairing"]["reference"]
    return ref, [n for n in rec["removed_own_amp_tracks"] if n != ref]


def build_table():
    from learn import arm_a_mega53 as A
    from learn import set3

    cat12, cat3 = _catalogs()
    parts = {}
    for slug in A.pool_slugs():
        part = A.f_part(slug)
        rec = json.loads((part["crop"] / "record.json").read_text())
        ref, alt = f_reference(slug, rec, cat12)
        if ref not in rec["included_mix_tracks"]:
            raise SystemExit(f"{slug}: the reference {ref} is not in the mix")
        tracks = {n: classify_f(n, ref, alt) for n in rec["included_mix_tracks"]}
        parts[slug] = {"band": A.pool_band(slug), "source": rec["source"], "song": rec["song"], "set": part["set"],
                       "reference": ref, "alternates_declared": alt,
                       "alternates_in_mix": [a for a in alt if a in rec["included_mix_tracks"]],
                       "ambiguous_to_rest": [n for n in rec["included_mix_tracks"] if AMBIGUOUS.search(base(n))],
                       "tracks": tracks}
    train = {}
    for s in cat12["sessions"]:
        g = s.get("group")
        if g not in IN_SCOPE_TRAIN + HIGH_GAIN_TRAIN:
            continue
        dis = {p.get("di") for p in s.get("parts", [])}
        files = sorted(s["files"])
        mix = list(s["mix_tracks"])
        tracks = {n: ("not_in_declared_mix" if n not in mix and n not in dis else classify_train(n, n in dis))
                  for n in files}
        train[f"{s['source']}/{s['song']}"] = {
            "band": g, "set": 12, "role": "in_scope" if g in IN_SCOPE_TRAIN else "high_gain",
            "tracks": tracks, "mix_list": [n for n in mix if tracks[n] not in ("dropped", "di")],
            "target_list": [n for n in mix if tracks[n] == "electric_guitar"],
            "no_electric_guitar_target": not any(tracks[n] == "electric_guitar" for n in mix)}
    for s in cat3["sessions"]:
        if s["band"] not in IN_SCOPE_TRAIN + HIGH_GAIN_TRAIN:
            continue
        root = set3.SET3_ROOT / s["path"]
        dis = {pathlib.Path(d["di"]).name for d in s.get("dis", [])}
        files = sorted({p.name for p in root.rglob("*.wav")})
        tracks = {n: classify_train(n, n in dis) for n in files}
        train[s["key"]] = {"band": s["band"], "set": 3,
                           "role": "in_scope" if s["band"] in IN_SCOPE_TRAIN else "high_gain",
                           "tracks": tracks, "mix_list": [n for n in files if tracks[n] in ("electric_guitar", "rest")],
                           "target_list": [n for n in files if tracks[n] == "electric_guitar"],
                           "no_electric_guitar_target": not any(v == "electric_guitar" for v in tracks.values())}
    return {"declared": "docs/separation-finetune-plan.md, Step 0", "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "classes_stage_f": F_CLASSES,
            "classes_training": ("electric_guitar", "rest", "di", "dropped", "not_in_declared_mix"),
            "rules": {"electric": "name has ElecGtr or starts with GTR; not a DI, keys, vox, acoustic or bounce",
                      "ambiguous_to_rest": "GTR KEYS AMP (keys through an amp), Eggy's VOX GTR, Quicksand's Intro mics",
                      "dropped": "pre-recorded bounces (JMK 'Pre Record Tracks', Renesans 'GTR Pre Rec' and the other "
                                 "'Pre Rec' bounces), Renesans' BAND CLICK, Eggy's master bounce: dropped from both "
                                 "mix and target (not listened to; Step 2 would listen before classing any)",
                      "quicksand_intro": "Quicksand's 32-35 Intro Close/Far files are 27.9 s long, silent across "
                                         "the stage-F context (it starts at 67.5 s), so their class has no effect",
                      "not_in_declared_mix": "sets 1-2 keep the catalogue's declared one-mic mix: other mics and "
                                             "files outside it (TF11, TF51, Ale Lak's Amp2, Eggy's master bounce) "
                                             "are excluded from mix and target; set-3 sessions have no declared mix, "
                                             "so every non-DI, non-dropped file counts (both mics of a guitar)",
                      "doubles": "a DT track is a double of the target when its guitar number matches the "
                                 "reference's, else of another guitar"},
            "stage_f": parts, "training": train}


def cmd_table():
    t = build_table()
    TABLE.write_text(json.dumps(t, indent=1, ensure_ascii=False) + "\n")
    n = {c: sum(v == c for p in t["stage_f"].values() for v in p["tracks"].values()) for c in F_CLASSES}
    print(f"track table: {len(t['stage_f'])} parts {n}; {len(t['training'])} training sessions -> {TABLE}")


# --- signals ------------------------------------------------------------------------------------------

def load_table():
    return json.loads(TABLE.read_text())


def session_root(slug):
    from learn import arm_a_mega53 as A
    from learn import separate as SEP

    part = A.f_part(slug)
    rec = json.loads((part["crop"] / "record.json").read_text())
    cat = _catalogs()[0] if part["set"] == 12 else A.shim_catalog(rec)
    s = [x for x in cat["sessions"] if x["source"] == rec["source"] and x["song"] == rec["song"]]
    assert len(s) == 1, slug
    return part, rec, SEP.DATA / s[0]["path"]


def load_tracks(slug, names):
    """{name: full-session mono float64}, exactly as `separate.context` loads them."""
    import numpy as np

    from analysis import io

    part, rec, root = session_root(slug)
    n = rec["session_frames"]
    out = {}
    for name in names:
        audio = io.load(root / name)
        assert audio.sha256 == rec["verified_source_sha256"][name], (slug, name)
        x = np.zeros(n, np.float64)
        m = audio.mono().astype(np.float32)[:n]
        x[:len(m)] = m
        out[name] = x
    return out


def context_window(rec):
    from learn import separate as SEP

    return SEP.window(rec["session_frames"], rec["excerpt_start_frame"], rec["excerpt_end_frame"], SEP.PAD_S * SR)


def stft(x):
    from scipy.signal import stft as _stft

    return _stft(x, SR, window="hann", nperseg=NFFT, noverlap=NFFT - HOP, boundary="zeros", padded=True)[2]


def istft(Z, n):
    import numpy as np
    from scipy.signal import istft as _istft

    y = _istft(Z, SR, window="hann", nperseg=NFFT, noverlap=NFFT - HOP, boundary=True)[1]
    out = np.zeros(n)
    out[:min(n, len(y))] = y[:n]
    return out


def wiener(mix, stem, passes=1):
    """Single-target Wiener on the mix: mask |S|²/(|S|²+|X−S|²) with S the stem; each extra pass
    re-estimates the powers from the previous pass's output (S ← T, noise ← X − T)."""
    import numpy as np

    X = stft(mix)
    s = np.asarray(stem, np.float64)
    for _ in range(passes):
        S, N = stft(s), stft(mix - s)
        ps, pn = np.abs(S) ** 2, np.abs(N) ** 2
        s = istft(X * ps / (ps + pn + 1e-20), len(mix))
    return s


def gain_fit(x, target):
    import numpy as np

    return float(np.dot(x, target) / (np.dot(x, x) + 1e-20))


def ensemble(mega, hd, mix):
    """0.5·M + 0.5·H, each gain-fitted to the mix first."""
    return 0.5 * gain_fit(mega, mix) * mega + 0.5 * gain_fit(hd, mix) * hd


def measures(x, ref):
    from learn import separator_screen as SCR
    from learn import stereo_mix_check as SMC

    return {"snr_db": SMC.snr_db(x, ref), "si_sdr_db": SCR.si_sdr(x, ref), "lsd_db": SMC.lsd_db(x, ref),
            "bright_diff_db": SMC.hf_ratio_db(x) - SMC.hf_ratio_db(ref)}


def energy_db(num, den):
    import numpy as np

    return float(10 * np.log10((np.sum(np.square(num)) + 1e-20) / (np.sum(np.square(den)) + 1e-20)))


def exposed_share(target, others, sec=SECTION_S * SR):
    """X: over the session's 10-s sections where the target's RMS reaches −40 dBFS, the share where
    the other electric guitars' energy sits 10 dB or more below the target's. -> (share, sections)."""
    import numpy as np

    k = len(target) // sec
    act = exp = 0
    for i in range(k):
        t = target[i * sec:(i + 1) * sec]
        if 10 * np.log10(np.mean(t ** 2) + 1e-20) < ACTIVE_DBFS:
            continue
        act += 1
        o = others[i * sec:(i + 1) * sec]
        exp += energy_db(o, t) <= EXPOSED_DB
    return (exp / act if act else None), act


def part_signals(slug, entry):
    """The crop signals and the session-level X for one part (no renders)."""
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import confirm_run as CR
    from learn import separator_screen as SCR

    part, rec, _ = session_root(slug)
    cs, ce = context_window(rec)
    off = rec["excerpt_start_frame"] - cs
    clog = json.loads(A.fdir("contexts", "log.json").read_text())
    if clog[slug]["offset"] != off:
        raise SystemExit(f"{slug}: offset {off} is not the stored {clog[slug]['offset']}")
    tr = entry["tracks"]
    full = load_tracks(slug, list(tr))
    ctx = {n: v[cs:ce] for n, v in full.items()}
    mix = sum(ctx.values())
    stored = np.load(A.fdir("contexts", f"{slug}.npy")).astype(np.float64)
    lineup = float(np.max(np.abs(mix.astype(np.float32) - stored)))
    cls = lambda *c: [n for n in tr if tr[n] in c]                                    # noqa: E731
    g_names = cls("target", "target_other_mic", "double_track_of_target", "double_track_of_other",
                  "other_electric_guitar")
    zero = np.zeros(ce - cs)
    G = sum((ctx[n] for n in g_names), zero)
    G_noDT = sum((ctx[n] for n in g_names if tr[n] != "double_track_of_other"), zero)
    G_mic = sum((ctx[n] for n in cls("target", "target_other_mic")), zero)
    other_names = cls("double_track_of_target", "double_track_of_other", "other_electric_guitar")
    O = sum((ctx[n] for n in other_names), zero)
    M = np.load(A.fdir("sep", "mega53", "full", f"{slug}.npy")).astype(np.float64)
    H = np.load(A.fdir("sep", "htdemucs", "full", f"{slug}.npy")).astype(np.float64)
    sig = {"M": M, "H": H, "G": G, "G_noDT": G_noDT, "G_mic": G_mic,
           "T1": wiener(stored, M, 1), "T2": wiener(stored, M, 2), "T3": ensemble(M, H, stored),
           "T4": SCR.blend(M, H)}
    crop = {k: v[off:off + CROP] for k, v in sig.items()}
    ref = CR.mono(part["crop"] / "reference.wav")
    tgt_full = full[entry["reference"]]
    o_full = sum((full[n] for n in other_names), np.zeros(len(tgt_full)))
    x_share, x_sections = exposed_share(tgt_full, o_full)
    stored_crops = {s: np.load(A.sep_crop(s, slug)).astype(np.float64) for s in ("mega53", "htdemucs")}
    checks = {"context_lineup_max_abs": lineup,
              "mega53_crop_max_abs": float(np.max(np.abs(crop["M"] - stored_crops["mega53"]))),
              "htdemucs_crop_max_abs": float(np.max(np.abs(crop["H"] - stored_crops["htdemucs"]))),
              "g_mic_minus_reference_max_abs": float(np.max(np.abs(crop["G_mic"] - ref)))}
    row = {"band": entry["band"], "gain_class": part["gain_class"], "checks": checks,
           "measures": {k: (measures(v, ref) if k != "G_mic" or checks["g_mic_minus_reference_max_abs"] > 1e-6
                            else {"identical_to_reference": True}) for k, v in crop.items()},
           "M_vs_G": measures(crop["M"], crop["G"]),
           "I_db": energy_db(O[off:off + CROP], ref) if other_names else None,
           "other_guitar_tracks": other_names,
           "X": x_share, "X_sections": x_sections}
    return row, crop["G"].astype(np.float32)


def cmd_measure():
    import numpy as np

    from learn import arm_a_mega53 as A

    A.require_heldout_ok()
    t = load_table()
    (OUT / "G" / "crop").mkdir(parents=True, exist_ok=True)
    path = OUT / "step0-parts.json"
    rows = json.loads(path.read_text()) if path.exists() else {}
    for slug in A.pool_slugs():
        if slug in rows:
            continue
        t0 = time.time()
        row, g = part_signals(slug, t["stage_f"][slug])
        if len(g) != CROP:
            raise SystemExit(f"{slug}: G crop {len(g)} samples")
        np.save(OUT / "G" / "crop" / f"{slug}.npy", g)
        row["seconds"] = round(time.time() - t0, 1)
        rows[slug] = row
        A._save(path, rows)
        print(slug, {k: round(v["snr_db"], 2) for k, v in row["measures"].items() if "snr_db" in v},
              "I", None if row["I_db"] is None else round(row["I_db"], 1), "X", row["X"], flush=True)
    bad = {s: r["checks"] for s, r in rows.items()
           if r["checks"]["context_lineup_max_abs"] > 1e-5 or r["checks"]["mega53_crop_max_abs"] > 1e-6
           or r["checks"]["htdemucs_crop_max_abs"] > 1e-6}
    A._save(OUT / "step0-check.json", {"ok": not bad, "problems": bad, "parts": len(rows)})
    if bad:
        raise SystemExit(f"Step 0 line-up checks fail: {bad}")
    print(f"measured {len(rows)} parts; checks pass")


# --- readings -----------------------------------------------------------------------------------------

def band_means(pairs):
    g = {}
    for b, v in pairs:
        g.setdefault(b, []).append(v)
    return {b: statistics.fmean(v) for b, v in g.items()}


def boot(pairs, n=N_BOOT, seed=SEED):
    """Band-weighted mean, 90% band bootstrap, and the one-sided p (share of draws ≤ 0)."""
    import random

    bm = band_means(pairs)
    bands = sorted(bm)
    rng = random.Random(seed)
    draws = sorted(statistics.fmean(bm[rng.choice(bands)] for _ in bands) for _ in range(n))
    return {"band_mean": statistics.fmean(bm.values()), "lo": draws[int(0.05 * n)], "hi": draws[int(0.95 * n)],
            "p_le_0": sum(d <= 0 for d in draws) / n, "band_median": statistics.median(bm.values()),
            "part_mean": statistics.fmean(v for _, v in pairs), "n": len(pairs), "bands": len(bands)}


def median_lobo(pairs):
    bm = band_means(pairs)
    bands = sorted(bm)
    med = statistics.median(bm.values())
    lobo = [statistics.median([bm[b] for b in bands if b != x]) for x in bands]
    return {"band_median": med, "lobo_min": min(lobo), "lobo_max": max(lobo), "bands": len(bands),
            "bands_above_0": sum(v > 0 for v in bm.values()), "band_values": bm}


def holm(ps, alpha=HOLM_ALPHA):
    """{name: survives} under Holm's step-down at alpha."""
    order = sorted(ps, key=lambda k: ps[k])
    out, stop = {}, False
    for i, k in enumerate(order):
        if not stop and ps[k] <= alpha / (len(order) - i):
            out[k] = True
        else:
            stop, out[k] = True, False
    return out


def r0a(rows):
    pairs = [(r["band"], r["measures"]["G"]["snr_db"] - r["measures"]["M"]["snr_db"]) for r in rows.values()]
    m = median_lobo(pairs)
    m["band_weighted"] = boot(pairs)
    m["reading"] = "step_1" if m["band_median"] > 0 else "stop_class_route"
    return m


def r0b(rows):
    out, ps = {}, {}
    for t in T_ORDER:
        d = [(r["band"], r["measures"][t]["snr_db"] - r["measures"]["M"]["snr_db"]) for r in rows.values()]
        lsd = [(r["band"], r["measures"][t]["lsd_db"] - r["measures"]["M"]["lsd_db"]) for r in rows.values()]
        si = [(r["band"], r["measures"][t]["si_sdr_db"] - r["measures"]["M"]["si_sdr_db"]) for r in rows.values()]
        br = [(r["band"], r["measures"][t]["bright_diff_db"] - r["measures"]["M"]["bright_diff_db"]) for r in rows.values()]
        out[t] = {"snr_gain": boot(d), "lsd_change": boot(lsd), "si_sdr_gain": boot(si), "brightness_change": boot(br)}
        ps[t] = out[t]["snr_gain"]["p_le_0"]
    surv = holm(ps)
    straight = None
    for t in T_ORDER:
        o = out[t]
        o["holm_survives"] = surv[t]
        o["lsd_ok"] = o["lsd_change"]["band_mean"] <= LSD_COST_DB
        o["post_process_candidate"] = surv[t] and o["lsd_ok"]
        o["meets_step3_rule"] = (o["snr_gain"]["band_mean"] >= GATE_POINT_DB and o["snr_gain"]["lo"] > GATE_LO_DB)
        if straight is None and o["post_process_candidate"] and o["meets_step3_rule"]:
            straight = t
    return {"variants": out, "straight_to_step3": straight}


def arm_a_part_contrasts():
    """Per part: the mean held-half log ratio YT − M and M − H over its directions (stored arm
    records, zero renders), and YT − M band-weighted with its band-clustered interval."""
    from learn import arm_a_mega53 as A
    from learn import perfect_sep_arm as P

    units = P.build_units()
    filters = {r: A.row_filter(r, "F", A.C.load_bleed_table(), {}) for r in P.ROWS if r != "no_lag_part"}
    filters["no_lag_part"] = lambda u: u["slug"] != P.LAG_PART
    yt_m = P.contrast(units, "YT", "M", filters)
    kept, _ = A.units_for(units, tuple(dict.fromkeys((*A.BASE, "XO", "YT"))))
    per = {}
    for a, b, k in (("YT", "M", "YT_minus_M"), ("M", "H", "M_minus_H")):
        for (slug, _, _), (_, _, _, v) in A.log_rows(kept, a, b).items():
            per.setdefault(slug, {}).setdefault(k, []).append(v)
    return yt_m, {s: {k: statistics.fmean(v) for k, v in d.items()} for s, d in per.items()}


def r0c(rows, per):
    from scipy.stats import spearmanr

    slugs = [s for s in rows if rows[s]["I_db"] is not None]
    I = [rows[s]["I_db"] for s in slugs]
    out = {"per_part": {s: {"I_db": rows[s]["I_db"], "X": rows[s]["X"], "X_sections": rows[s]["X_sections"],
                            "other_guitar_tracks": len(rows[s]["other_guitar_tracks"])} for s in rows}}
    snr_mh = [rows[s]["measures"]["M"]["snr_db"] - rows[s]["measures"]["H"]["snr_db"] for s in slugs]
    for name, ys in (("M_minus_H_arm_a", [per[s]["M_minus_H"] for s in slugs]),
                     ("YT_minus_M_arm_a", [per[s]["YT_minus_M"] for s in slugs]),
                     ("M_minus_H_snr_db", snr_mh),
                     ("M_snr_db", [rows[s]["measures"]["M"]["snr_db"] for s in slugs])):
        r = spearmanr(I, ys)
        out[f"spearman_I_vs_{name}"] = {"rho": float(r.statistic), "p": float(r.pvalue), "n": len(slugs)}
    out["G_noDT_minus_G_snr"] = boot([(r["band"], r["measures"]["G_noDT"]["snr_db"] - r["measures"]["G"]["snr_db"])
                                      for r in rows.values()])
    mic = [r["measures"]["G_mic"] for r in rows.values()]
    out["G_mic"] = ("identical to reference.wav on every part (the declared mixes hold only the reference mic)"
                    if all(m.get("identical_to_reference") for m in mic) else
                    boot([(r["band"], r["measures"]["G_mic"]["snr_db"] - r["measures"]["G"]["snr_db"])
                          for r in rows.values() if "snr_db" in r["measures"]["G_mic"]]))
    out["brightness"] = {s: {k: rows[s]["measures"][k]["bright_diff_db"] for k in ("M", "H", "G", *T_ORDER)}
                         for s in ("cambridge-magilla-elecgtr1", "telefunken-Russian_Cream-GTR_1")}
    out["I_band_weighted"] = boot([(rows[s]["band"], rows[s]["I_db"]) for s in slugs])
    xs = [(rows[s]["band"], rows[s]["X"]) for s in slugs if rows[s]["X"] is not None]
    out["X_band_weighted"] = boot(xs) if xs else None
    out["parts_with_other_guitar"] = len(slugs)
    return out


def summary_table(rows):
    out = {}
    for k in SIGNALS:
        ms = [r["measures"][k] for r in rows.values()]
        if all("snr_db" in m for m in ms):
            out[k] = {q: boot([(r["band"], r["measures"][k][q]) for r in rows.values()])
                      for q in ("snr_db", "si_sdr_db", "lsd_db", "bright_diff_db")}
    out["M_vs_G"] = {q: boot([(r["band"], r["M_vs_G"][q]) for r in rows.values()]) for q in ("snr_db", "si_sdr_db")}
    return out


def cmd_report():
    from learn import arm_a_mega53 as A

    if not (A._load(OUT / "step0-check.json") or {}).get("ok"):
        raise SystemExit("run `measure` first (its checks must pass)")
    rows = json.loads((OUT / "step0-parts.json").read_text())
    if len(rows) != len(A.pool_slugs()):
        raise SystemExit(f"{len(rows)} parts measured, not {len(A.pool_slugs())}")
    yt_m, per = arm_a_part_contrasts()
    multi = {k: r for k, r in rows.items() if r["I_db"] is not None}
    rep = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "parts": len(rows), "summary": summary_table(rows),
           "summary_multi_guitar_parts": summary_table(multi),           # G equals the target on single-guitar parts
           "R0a_multi_guitar_parts": r0a(multi),
           "R0a": r0a(rows), "R0b": r0b(rows), "R0c": r0c(rows, per), "YT_minus_M": yt_m,
           "per_part_arm_a": per}
    A._save(OUT / "step0-report.json", rep)
    s = rep["summary"]
    for k in s:
        if k != "M_vs_G":
            print(f"  {k:7s} SNR {s[k]['snr_db']['band_mean']:+.2f} [{s[k]['snr_db']['lo']:+.2f}, {s[k]['snr_db']['hi']:+.2f}]"
                  f"  LSD {s[k]['lsd_db']['band_mean']:.2f}  bright {s[k]['bright_diff_db']['band_mean']:+.2f}")
    print("  M vs G SNR", round(s["M_vs_G"]["snr_db"]["band_mean"], 2))
    a = rep["R0a"]
    print(f"R0a: band median G − M {a['band_median']:+.2f} dB (LOBO {a['lobo_min']:+.2f} to {a['lobo_max']:+.2f}), "
          f"{a['bands_above_0']}/{a['bands']} bands above 0 -> {a['reading']}")
    for t, o in rep["R0b"]["variants"].items():
        g = o["snr_gain"]
        print(f"R0b {t}: {g['band_mean']:+.2f} [{g['lo']:+.2f}, {g['hi']:+.2f}] p {g['p_le_0']:.4f} holm {o['holm_survives']} "
              f"LSD {o['lsd_change']['band_mean']:+.2f} candidate {o['post_process_candidate']} step3 {o['meets_step3_rule']}")
    print("R0b straight to Step 3:", rep["R0b"]["straight_to_step3"])
    c = rep["R0c"]
    print("R0c I", round(c["I_band_weighted"]["band_mean"], 1), "X", c["X_band_weighted"] and round(c["X_band_weighted"]["band_mean"], 2),
          {k: round(v["rho"], 2) for k, v in c.items() if k.startswith("spearman")})
    print("YT − M:", json.dumps((yt_m["rows"]["all"] or {}).get("all"), default=str))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("table", "measure", "report"))
    a = ap.parse_args(argv)
    {"table": cmd_table, "measure": cmd_measure, "report": cmd_report}[a.cmd]()


if __name__ == "__main__":
    main()
