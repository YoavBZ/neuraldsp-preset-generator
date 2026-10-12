#!/usr/bin/env python3
"""Set 6's DI-role rule, calibrated on DEVELOPMENT data only (sets 1-2 and set 3 development).

MedleyDB names no DI, so set 6 must say which track of a same-take pair of guitar raw tracks
is a DI. This script measures candidate cues on labelled development pairs, where the roles
are known from the session track names:

  * positives: a part's DI against each of its amp tracks (reference and alternates);
  * negatives: two amp tracks of one part (two microphones on one amp, close/far, Amp1/Amp2),
    amp tracks of different parts, and DI against DI (a duplicate or split DI).

Every unordered pair of a session's guitar tracks (DIs and amp tracks of the catalogued parts)
gets set 4's waveform same-take test (gcc.windowed_gcc, unchanged thresholds), as MedleyDB's
pairs did; only same-take pairs are scored. For each same-take pair and each orientation
(x as the DI candidate, y as its amp track) it records:

  * the linear transfer x -> y (H1 = Sxy / Sxx over frames where both play, after the
    waveform lag and polarity), in bands, and its coherence;
  * the plain power ratio Syy / Sxx in the same bands (the old per-track HF-share cue);
  * set 3's gain measures and class (gainmeasure.py / classify.py, the bytes sets 4-6 use).

No held-out session is opened (sets 1-2 held-out sessions and parts, set 3 held-out sessions,
sets 4-6 are never listed). Nothing is rendered, scored, separated or listened to.

    .venv/bin/python research/set6_di_role_calibration.py measure   # audio -> pairs JSON
    .venv/bin/python research/set6_di_role_calibration.py evaluate  # JSON only -> table
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
from multiprocessing import Pool

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
HOME = pathlib.Path.home() / "ndsp-presets" / "references"
TOOLS = HOME / "datasets-set4" / "_tools"
OUT = HOME / "datasets-medleydb" / "_tools" / "di_role_calibration"
PAIRS = OUT / "dev_pairs.json"
TRACKS = OUT / "dev_tracks.json"
SETS_1_2 = REPO / "docs" / "validation-datasets.json"
SET3 = REPO / "docs" / "validation-set3.json"
SET3_CATALOG = HOME / "datasets-set3" / "catalog.json"

BANDS = [(100, 200), (200, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 6000),
         (6000, 8000), (8000, 10000), (10000, 14000)]
MAX_FRAMES = 4000


# --- the development pairs -----------------------------------------------------------

def development_sessions() -> list[dict]:
    """[{key, band, root, tracks: {name: (role, part)}}], development only."""
    out = []
    d12 = json.loads(SETS_1_2.read_text())
    for s in d12["sessions"]:
        if s["split"] != "development":
            continue
        tracks = {}
        for p in s["parts"]:
            if p.get("di"):
                tracks.setdefault(p["di"], ("di", p["part"]))
            for a in [p.get("reference"), *(p.get("alternate") or [])]:
                if a:
                    tracks.setdefault(a, ("amp", p["part"]))
        key = s["path"] if s["source"] != "guitar-techs" else f"{s['path']}/{s['parts'][0]['part']}"
        out.append({"key": f"sets12/{key}", "band": band_1_2(s["path"]),
                    "root": str(HOME / "datasets" / s["path"]), "tracks": tracks})
    s3 = json.loads(SET3.read_text())
    split = {s["key"]: (s["split"], s["band"]) for s in s3["sessions"]}
    cat = json.loads(SET3_CATALOG.read_text())
    for s in cat["sessions"]:
        sp, band = split.get(s["key"], (None, None))
        if sp != "development":
            continue
        tracks = {}
        for p in s["parts"]:
            if p.get("di"):
                tracks.setdefault(p["di"], ("di", p["part"]))
            for a in [p.get("reference"), *(p.get("alternate") or [])]:
                if a:
                    tracks.setdefault(a, ("amp", p["part"]))
        out.append({"key": f"set3/{s['key']}", "band": band, "root": str(HOME / "datasets-set3" / s["path"]),
                    "tracks": tracks})
    return out


BANDS_1_2 = [("Haviland", "Rebecca Haviland"), ("ChrisColtraine", "Chris Coltraine"),
             ("AdamBuckley", "Adam Buckley"), ("AleLak", "Ale Lak"), ("AtlantisBound", "Atlantis Bound"),
             ("EatTheFeeder", "Eat The Feeder"), ("StarnesAndShah", "Starnes And Shah"),
             ("TheTravellingBand", "The Travelling Band"), ("MR1003", "MR1003"),
             ("Dom McLennon", "Dom McLennon"), ("Doom Flamingo", "Doom Flamingo"), ("Eggy", "Eggy"),
             ("Swatkins", "Swatkins"), ("Bernard Purdie", "Bernard Purdie Tribute All Stars"),
             ("guitar-techs", "Guitar-TECHS P3")]


def band_1_2(path):
    """A band name for a sets-1-2 session path (for leave-band-out only)."""
    for k, v in BANDS_1_2:
        if k in path:
            return v
    return path.split("/", 1)[1]


def label(ra, rb):
    (role_a, part_a), (role_b, part_b) = ra, rb
    if {role_a, role_b} == {"di", "amp"}:
        return "di_amp" if part_a == part_b else "di_amp_other_part"
    if role_a == role_b == "amp":
        return "amp_amp_same_part" if part_a == part_b else "amp_amp_other_part"
    return "di_di"


# --- measuring (audio) ---------------------------------------------------------------

def _load(path):
    import numpy as np
    import soundfile as sf
    x, sr = sf.read(path, always_2d=True, dtype="float32")
    return x.mean(axis=1).astype(np.float64), int(sr)


def oriented_cues(x, y, sr, lag, pol):
    """x the DI candidate, y its amp track; y later than x by `lag` samples."""
    import numpy as np
    if lag > 0:
        y = y[lag:]
    elif lag < 0:
        y = np.concatenate([np.zeros(-lag), y])
    y = pol * y
    n = min(len(x), len(y))
    x, y = x[:n], y[:n]
    F = 4096 if sr < 60000 else 8192
    H = F // 2
    nf = (n - F) // H + 1
    if nf < 20:
        return None
    idx = np.arange(F)[None, :] + H * np.arange(nf)[:, None]
    rx = 20 * np.log10(np.sqrt(np.mean(x[idx] ** 2, axis=1)) + 1e-12)
    ry = 20 * np.log10(np.sqrt(np.mean(y[idx] ** 2, axis=1)) + 1e-12)
    act = np.flatnonzero((rx >= rx.max() - 40) & (ry >= ry.max() - 40))
    if len(act) < 20:
        return None
    if len(act) > MAX_FRAMES:
        act = act[np.linspace(0, len(act) - 1, MAX_FRAMES).astype(int)]
    w = np.hanning(F)
    Sxx = Syy = 0.0
    Sxy = 0j
    for chunk in np.array_split(act, max(1, len(act) // 500)):
        X = np.fft.rfft(x[idx[chunk]] * w, axis=1)
        Y = np.fft.rfft(y[idx[chunk]] * w, axis=1)
        Sxx = Sxx + (np.abs(X) ** 2).sum(0)
        Syy = Syy + (np.abs(Y) ** 2).sum(0)
        Sxy = Sxy + (Y * np.conj(X)).sum(0)
    f = np.fft.rfftfreq(F, 1 / sr)
    h1 = np.abs(Sxy) ** 2 / (Sxx ** 2 + 1e-30)          # |H1|^2
    coh = np.abs(Sxy) ** 2 / (Sxx * Syy + 1e-30)
    out = {"frames": int(len(act)), "h1_db": {}, "power_ratio_db": {}, "coherence": {}}
    for lo, hi in BANDS:
        m = (f >= lo) & (f < hi)
        if not m.any() or hi > sr / 2:
            continue
        k = f"{lo}-{hi}"
        out["h1_db"][k] = round(float(10 * np.log10(np.mean(h1[m]) + 1e-30)), 2)
        out["power_ratio_db"][k] = round(float(10 * np.log10(Syy[m].sum() / (Sxx[m].sum() + 1e-30) + 1e-30)), 2)
        out["coherence"][k] = round(float(np.mean(coh[m])), 4)
    return out


def measure_session(sess):
    import numpy as np
    sys.path[:0] = [str(TOOLS)]
    import gcc
    import gainmeasure
    from classify import classify
    from set4 import SUPP_IN_STEP, SUPP_PSR
    root = pathlib.Path(sess["root"])
    names = sorted(sess["tracks"])
    audio = {}
    for nme in names:
        p = root / nme
        if not p.exists():
            hits = [q for q in root.rglob(pathlib.PurePosixPath(nme).name) if not q.name.startswith("._")]
            if len(hits) != 1:
                raise FileNotFoundError(f"{root}/{nme}: {len(hits)} matches")
            p = hits[0]
        audio[nme] = _load(str(p))
    rows = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            xa, sr = audio[a]
            xb, srb = audio[b]
            if sr != srb:
                rows.append({"a": a, "b": b, "error": f"rates {sr} {srb}"})
                continue
            n = min(len(xa), len(xb))
            g = gcc.windowed_gcc(xb[:n], xa[:n], sr)   # b as the 'amp': lag > 0 when b is later
            g.pop("lags", None)
            same = bool(g.get("windows") and g["in_step_fraction"] >= SUPP_IN_STEP
                        and g["median_peak_to_sidelobe"] >= SUPP_PSR)
            row = {"a": a, "b": b, "role_a": sess["tracks"][a], "role_b": sess["tracks"][b],
                   "label": label(sess["tracks"][a], sess["tracks"][b]), "sample_rate": sr,
                   "waveform": g, "same_take": same}
            if same:
                lag, pol = g["median_lag_samples"], g.get("polarity") or 1
                for key, x, y, l in (("a_as_di", xa[:n], xb[:n], lag), ("b_as_di", xb[:n], xa[:n], -lag)):
                    c = oriented_cues(x, y, sr, l, pol)
                    m = gainmeasure.measures(pol * y, x, sr, l)
                    cls = classify(m) if m else (None, None, None, None)
                    row[key] = {"cues": c, "gain_measures": m, "gain_class": cls[0], "clean_vs_driven": cls[3]}
            rows.append(row)
    return {"key": sess["key"], "band": sess["band"], "pairs": rows}


def measure(workers=3):
    sessions = development_sessions()
    OUT.mkdir(parents=True, exist_ok=True)
    done = json.loads(PAIRS.read_text()) if PAIRS.exists() else {"sessions": []}
    have = {s["key"] for s in done["sessions"]}
    todo = [s for s in sessions if s["key"] not in have]
    print(f"{len(sessions)} development sessions, {len(todo)} to measure", flush=True)
    with Pool(workers) as pool:
        for r in pool.imap_unordered(measure_session, todo):
            done["sessions"].append(r)
            PAIRS.write_text(json.dumps(done, indent=1))
            st = sum(p.get("same_take", False) for p in r["pairs"])
            print("DONE", r["key"], len(r["pairs"]), "pairs,", st, "same take", flush=True)


def track_cues(x, sr):
    """Per-track DI-role cues over the track's playing frames (within 40 dB of its loudest frame).
    The same code as the MedleyDB pairing script's track_cues (tmp/set6/pair.py), so the
    MedleyDB inventory's per-track cues are comparable."""
    import numpy as np
    F, H = 4096, 2048
    nf = (len(x) - F) // H + 1
    if nf < 20: return None
    idx = np.arange(F)[None, :] + H * np.arange(nf)[:, None]
    r = np.sqrt(np.mean(x[idx] ** 2, axis=1)) + 1e-12
    db = 20 * np.log10(r)
    act = db >= db.max() - 40
    sel = idx[act]
    S = 0.0
    for chunk in np.array_split(sel, max(1, len(sel) // 500)):
        S = S + (np.abs(np.fft.rfft(x[chunk] * np.hanning(F), axis=1)) ** 2).sum(0)
    f = np.fft.rfftfreq(F, 1 / sr)
    hf = 10 * np.log10(S[(f >= 5000) & (f <= 10000)].sum() / (S[(f >= 200) & (f < 4000)].sum() + 1e-20) + 1e-20)
    W = sr; cr = []
    for s0 in range(0, len(x) - W, W // 2):
        k0 = s0 // H
        if k0 + W // H > len(act) or not act[k0:k0 + W // H - 1].all(): continue
        y = x[s0:s0 + W]; cr.append(20 * np.log10(np.max(np.abs(y)) / (np.sqrt(np.mean(y ** 2)) + 1e-12)))
    return {"active_frames": int(act.sum()), "hf_5_10k_vs_0_2_4k_db": round(float(hf), 2),
            "crest1s_db": round(float(np.median(cr)), 2) if cr else None, "crest1s_windows": len(cr),
            "frame_level_spread_db": round(float(np.std(db[act])), 2)}


def _tracks_of(sess):
    root = pathlib.Path(sess["root"])
    out = {}
    for nme in sorted(sess["tracks"]):
        p = root / nme
        if not p.exists():
            p = next(q for q in root.rglob(pathlib.PurePosixPath(nme).name) if not q.name.startswith("._"))
        x, sr = _load(str(p))
        out[nme] = {"role": sess["tracks"][nme], "sample_rate": sr, "cues": track_cues(x, sr)}
    return sess["key"], out


def measure_tracks(workers=3):
    sessions = development_sessions()
    with Pool(workers) as pool:
        res = dict(pool.imap_unordered(_tracks_of, sessions))
    TRACKS.write_text(json.dumps(res, indent=1))
    print(len(res), "sessions;", sum(len(v) for v in res.values()), "tracks")


# --- the rule (JSON only) ------------------------------------------------------------

LO = ("500-1000", "1000-2000")
HI = ("6000-8000", "8000-10000")
COH_BANDS = ("200-500", "500-1000", "1000-2000")
SUMMARY = OUT / "calibration.json"
FA_BAR = 0.10            # the bar: leave-band-out false accepts on all development negatives


def _nz(v, d):
    return d if v is None or v != v else v


def _orient(x, y, o, tracks):
    import numpy as np
    c = o["cues"]
    g = o["gain_measures"] or {}
    return {"x": x, "y": y, "cls": o["gain_class"],
            "h1": float(np.mean([c["h1_db"][k] for k in HI]) - np.mean([c["h1_db"][k] for k in LO])),
            "crest": _nz(g.get("crest1s_drop_db"), None), "slope": _nz(g.get("level_slope"), None),
            "hf_adv": tracks[x]["cues"]["hf_5_10k_vs_0_2_4k_db"] - tracks[y]["cues"]["hf_5_10k_vs_0_2_4k_db"]}


def rows():
    """Same-take development pairs with both orientations' cues and the true roles."""
    import numpy as np
    d = json.loads(PAIRS.read_text())
    T = json.loads(TRACKS.read_text())
    out = []
    for s in d["sessions"]:
        tr = T[s["key"]]
        for p in s["pairs"]:
            if not p.get("same_take") or not (p["a_as_di"]["cues"] and p["b_as_di"]["cues"]):
                continue
            A = _orient(p["a"], p["b"], p["a_as_di"], tr)
            B = _orient(p["b"], p["a"], p["b_as_di"], tr)
            ra, rb = p["role_a"][0], p["role_b"][0]
            di = p["a"] if (ra, rb) == ("di", "amp") else p["b"] if (ra, rb) == ("amp", "di") else None
            coh = float(np.mean([p["a_as_di"]["cues"]["coherence"][k] for k in COH_BANDS]))
            out.append({"band": s["band"], "session": s["key"], "label": p["label"], "di": di,
                        "lag": p["waveform"]["median_lag_samples"], "sample_rate": p["sample_rate"],
                        "coherence": coh, "A": A, "B": B,
                        "gain_class": (A if di == p["a"] else B)["cls"] if di else None})
    return out


# The rule families. Each returns (accepted, di_name) for an unordered same-take pair.

def declared_rule(r, p=None):
    """Set 6 as first declared (f1918cc): the earlier track is the DI, lag 3 samples-5 ms,
    driven: crest drop >= 3 dB; clean: per-track 5-10 kHz share advantage >= 6 dB."""
    lag = r["lag"]
    X = r["A"] if lag >= 0 else r["B"]
    if abs(lag) < 3 or abs(lag) > 0.005 * r["sample_rate"]:
        return False, None
    if X["cls"] in ("crunch", "high-gain"):
        return _nz(X["crest"], -99) >= 3.0, X["x"]
    return X["hf_adv"] >= 6.0, X["x"]


def driven_rule(r, p):
    """Coherence (0.2-2 kHz) in [lo, hi] and the larger crest drop >= d; that orientation's
    candidate is the DI."""
    lo, hi, d = p
    if not lo <= r["coherence"] <= hi:
        return False, None
    X = max((r["A"], r["B"]), key=lambda o: _nz(o["crest"], -99))
    return _nz(X["crest"], -99) >= d, X["x"]


def two_branch_rule(r, p):
    """Driven branch as driven_rule (lo, hi, d); otherwise a clean branch: coherence <= c or
    the steeper linear-transfer roll-off (6-10 kHz against 0.5-2 kHz) <= t dB, the DI being the
    orientation with the lower level slope (the amp track compresses)."""
    lo, hi, d, c, t = p
    ok, di = driven_rule(r, (lo, hi, d))
    if ok:
        return ok, di
    if r["coherence"] < lo:
        return False, None
    if r["coherence"] <= c or min(r["A"]["h1"], r["B"]["h1"]) <= t:
        X = min((r["A"], r["B"]), key=lambda o: _nz(o["slope"], 9))
        return True, X["x"]
    return False, None


def _grid(family):
    import numpy as np
    drv = [(lo, hi, float(d)) for lo in (0.0, 0.05, 0.1, 0.2) for hi in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
           for d in np.arange(-1, 6.01, 0.5)]
    if family == "driven":
        return drv
    return [(0.05, 0.7, 1.0, round(float(c), 2), float(t)) for c in np.arange(0.5, 0.96, 0.05)
            for t in (-40, -35, -30, -25, -22, -20, -18, -15)] + \
           [(0.05, hi, d, round(float(c), 2), float(t)) for hi in (0.6, 0.8) for d in (0.5, 1.5)
            for c in (0.6, 0.7, 0.8) for t in (-30, -22, -15)]


FAMILIES = {"driven": driven_rule, "two_branch": two_branch_rule}


def _score(rule, p, pos, neg):
    tp = sum(1 for r in pos if (lambda a: a[0] and a[1] == r["di"])(rule(r, p)))
    fa = sum(rule(r, p)[0] for r in neg)
    return tp, fa


def _fit(rule, grid, pos, neg):
    """Most true accepts (right DI) with false accepts <= FA_BAR; ties: fewer false accepts."""
    def key(p):
        tp, fa = _score(rule, p, pos, neg)
        return (fa <= FA_BAR * len(neg), tp, -fa)
    return max(grid, key=key)


def _table(rule, p, pos, neg):
    acc, tot, wrong = collections.Counter(), collections.Counter(), 0
    for r in pos:
        tot[r["gain_class"]] += 1
        ok, di = rule(r, p)
        if ok and di == r["di"]:
            acc[r["gain_class"]] += 1
        elif ok:
            wrong += 1
    fa = collections.Counter(r["label"] for r in neg if rule(r, p)[0])
    return {"recall": {c: [acc[c], tot[c]] for c in ("clean", "crunch", "high-gain")},
            "recall_all": [sum(acc.values()), len(pos)], "accepted_wrong_orientation": wrong,
            "false_accepts": [sum(fa.values()), len(neg)], "false_accepts_by_label": dict(fa)}


def evaluate():
    R = rows()
    pos = [r for r in R if r["di"]]
    neg = [r for r in R if not r["di"]]
    bands = sorted({r["band"] for r in R})
    out = {"pairs": {"positives": len(pos), "negatives": len(neg),
                     "negatives_by_label": dict(collections.Counter(r["label"] for r in neg)),
                     "positives_by_class": dict(collections.Counter(r["gain_class"] for r in pos)),
                     "bands": len(bands), "negative_bands": len({r["band"] for r in neg})},
           "fa_bar": FA_BAR, "declared_rule": _table(declared_rule, None, pos, neg), "families": {}}
    for name, rule in FAMILIES.items():
        grid = _grid(name)
        full = _fit(rule, grid, pos, neg)
        # leave one band out: fit on the other bands, apply to the held band
        acc, tot, fa, wrong, chosen = collections.Counter(), collections.Counter(), collections.Counter(), 0, []
        for b in bands:
            P = [r for r in pos if r["band"] != b]
            N = [r for r in neg if r["band"] != b]
            p = _fit(rule, grid, P, N)
            chosen.append(list(p))
            for r in pos:
                if r["band"] == b:
                    tot[r["gain_class"]] += 1
                    ok, di = rule(r, p)
                    acc[r["gain_class"]] += bool(ok and di == r["di"])
                    wrong += bool(ok and di != r["di"])
            for r in neg:
                if r["band"] == b and rule(r, p)[0]:
                    fa[r["label"]] += 1
        out["families"][name] = {
            "parameters_all_bands": list(full), "in_sample": _table(rule, full, pos, neg),
            "leave_band_out": {"recall": {c: [acc[c], tot[c]] for c in ("clean", "crunch", "high-gain")},
                               "recall_all": [sum(acc.values()), len(pos)],
                               "accepted_wrong_orientation": wrong,
                               "false_accepts": [sum(fa.values()), len(neg)],
                               "false_accepts_by_label": dict(fa),
                               "parameters_chosen": dict(collections.Counter(map(str, chosen)).most_common(3))}}
    SUMMARY.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure")
    m.add_argument("--workers", type=int, default=3)
    sub.add_parser("tracks")
    sub.add_parser("evaluate")
    a = ap.parse_args()
    if a.cmd == "measure":
        measure(min(a.workers, 3))
    elif a.cmd == "tracks":
        measure_tracks(3)
    else:
        evaluate()


if __name__ == "__main__":
    main()
