"""Multi-section matching (`docs/multi-section-plan.md`). Development only, the true DI.

    .venv/bin/python -m learn.multi_section sections            # step 1: zero renders
    .venv/bin/python -m learn.multi_section run --worker 0/2    # step 2: one render process
    .venv/bin/python -m learn.multi_section report              # step 2: readout, zero renders

Step 1 cuts each development part's whole session into 10-s sections where the DI plays,
measures per section the guitar-in-mix SNR and a zero-render "tone curve" (the amp track's
long-term spectrum less the DI's), and flags bleed from the bleed audit. Step 2 asks, with the
true DI, whether settings searched on one section transfer to the part's other sections, and
whether a search over three sections at once transfers better.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import random
import statistics
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
OUT = HOME / "learn/multi-section"
SR = 48000
LATENCY = 52

# --- step 1: sections (declared in the plan) ---------------------------------------------------
SEC_S = 10.0                     # a section is 10 s, like every crop
HOP_S = 5.0                      # grid: 10-s windows every 5 s from the session start
FRAME, FHOP = 2048, 1024         # crop rule 2's frames
PLAY_DB = 40.0                   # a frame plays when within 40 dB of the DI's loudest frame (session)
MIN_ACTIVE = 0.80                # share of the section's frames that play
MIN_ACTIVE_HALF = 0.60           # ... and of each judge half's frames (1.0-5.5 s, 5.5-10 s)
HALVES = {"A": (1.0, 5.5), "B": (5.5, 10.0)}
# The tone curve: third-octave bands 100 Hz - 8 kHz, amp track less DI (dB), on frames that play,
# mean removed (so it is the shape, not the level). The level offset is reported separately.
TONE_LO, TONE_HI = 100.0, 8000.0
LOW_SNR_DB = -15.0               # guitar-in-full-mix ratio below this flags a section low-SNR (about 10% of sections)
# Stage F's 21 fresh parts (`learn/arm-a-mega53/report-F.json`): used once; never touched here.
STAGE_F = ("cambridge-It_Was_My_Fault_For_Waiting-ElecGtr3", "cambridge-Passing_Ships-ElecGtr2",
           "cambridge-Passing_Ships-ElecGtr4", "cambridge-Quicksand-ElecGtr2", "cambridge-Signs-ElecGtr3",
           "cambridge-Today's_The_Day-ElecGtr07", "cambridge-colour-me-red-elecgtr02",
           "cambridge-colour-me-red-elecgtr03", "cambridge-femme-elecgtr5", "cambridge-get-out-of-bed-elecgtr2",
           "cambridge-let-s-dance-elecgtr3", "cambridge-let-s-dance-elecgtr4", "cambridge-magilla-elecgtr1",
           "cambridge-wickerman-elecgtr1", "cambridge-wickerman-elecgtr2", "cambridge-wickerman-elecgtr3",
           "cambridge-wickerman-elecgtr7", "telefunken-Gym_Hours-GTR_2", "telefunken-Russian_Cream-GTR_1",
           "telefunken-She's_Gone-GTR", "telefunken-Strangest_Places-GTR")
LABEL_PARTS = PLUGIN_ROOT / "docs/label-table-parts.json"
LEDGER = PLUGIN_ROOT / "docs/dev-test-ledger.json"
BLEED = PLUGIN_ROOT / "docs/audits/bleed-2026-10-16/bleed-table.json"


def pool():
    """slug -> part record: the label table's clean and crunch development parts less stage F."""
    parts = json.loads(LABEL_PARTS.read_text())["parts"]
    out = {s: p for s, p in parts.items() if s not in STAGE_F and p["gain_class"] in ("clean", "crunch")}
    assert len(out) == len(parts) - len(STAGE_F), (len(out), len(parts))
    return out


def step3_parts():
    """Step 3's 24 parts (the ledger's song-settings entry): the first parts step 2 runs."""
    tests = {t["test_id"]: t for t in json.loads(LEDGER.read_text())["tests"]}
    return tuple(tests["song-settings"]["parts"])


# --- pure functions (unit-tested) ---------------------------------------------------------------

def frame_db(x, frame=FRAME, hop=FHOP):
    import numpy as np

    x = np.asarray(x, np.float64)
    if len(x) < frame:
        x = np.pad(x, (0, frame - len(x)))
    n = 1 + (len(x) - frame) // hop
    idx = np.arange(frame)[None, :] + hop * np.arange(n)[:, None]
    return 10 * np.log10(np.mean(x[idx] ** 2, axis=1) + 1e-30)


def playing(di_db, play_db=PLAY_DB):
    """Frames within `play_db` of the loudest frame (crop rule 2's test, over the whole session)."""
    import numpy as np

    if di_db.max() < -200.0:
        return np.zeros(len(di_db), bool)
    return di_db >= di_db.max() - play_db


def frames_in(start, end, n_frames, frame=FRAME, hop=FHOP):
    """Indices of the frames that lie wholly inside samples [start, end) (crop rule 2's span)."""
    lo = -(-start // hop)
    hi = (end - frame) // hop + 1
    return range(max(0, lo), min(n_frames, hi))


def grid(n_samples, sec_s=SEC_S, hop_s=HOP_S, sr=SR):
    """Start samples of the 10-s grid windows that fit in the session."""
    L, h = int(sec_s * sr), int(hop_s * sr)
    return list(range(0, n_samples - L + 1, h))


def section_activity(play, start, sr=SR, sec_s=SEC_S):
    """(share over the section, {half: share}) of frames that play."""
    import numpy as np

    L = int(sec_s * sr)
    whole = frames_in(start, start + L, len(play))
    out = {}
    for h, (a, b) in HALVES.items():
        r = frames_in(start + int(a * sr), start + int(b * sr), len(play))
        out[h] = float(np.mean(play[r.start:r.stop])) if len(r) else 0.0
    return (float(np.mean(play[whole.start:whole.stop])) if len(whole) else 0.0), out


def passes(share, halves, min_active=MIN_ACTIVE, min_half=MIN_ACTIVE_HALF):
    return share >= min_active and all(v >= min_half for v in halves.values())


def disjoint(starts, sec_s=SEC_S, sr=SR):
    """Greedy earliest-first: passing windows that don't overlap (the material counted)."""
    out, end = [], -1
    for s in sorted(starts):
        if s >= end:
            out.append(s)
            end = s + int(sec_s * sr)
    return out


def third_octaves(lo=TONE_LO, hi=TONE_HI):
    import numpy as np

    k = np.arange(math.floor(3 * math.log2(lo / 1000)), math.ceil(3 * math.log2(hi / 1000)) + 1)
    return 1000.0 * 2.0 ** (k / 3)


def band_power(x, mask_frames=None, nfft=4096, hop=2048, sr=SR):
    """Mean power per third-octave band over the (playing) frames; None if no frame is kept."""
    import numpy as np

    x = np.asarray(x, np.float64)
    if len(x) < nfft:
        return None
    n = 1 + (len(x) - nfft) // hop
    idx = np.arange(nfft)[None, :] + hop * np.arange(n)[:, None]
    P = np.abs(np.fft.rfft(x[idx] * np.hanning(nfft), axis=1)) ** 2
    if mask_frames is not None:
        P = P[np.asarray(mask_frames[:n], bool)]
    if len(P) == 0:
        return None
    f = np.fft.rfftfreq(nfft, 1 / sr)
    out = []
    for fc in third_octaves():
        m = (f >= fc * 2 ** (-1 / 6)) & (f < fc * 2 ** (1 / 6))
        out.append(P[:, m].sum(1).mean())
    return np.asarray(out)


def tone_curve(ref, di, lag=0, sr=SR):
    """(shape dB per band, mean removed; level offset dB): the amp track less the DI, on frames
    where the DI plays. `lag`: samples the amp track lags the DI (aligned before analysis)."""
    import numpy as np

    ref, di = np.asarray(ref, np.float64), np.asarray(di, np.float64)
    if lag > 0:
        ref, di = ref[lag:], di[:len(di) - lag]
    elif lag < 0:
        ref, di = ref[:len(ref) + lag], di[-lag:]
    db = frame_db(di, 4096, 2048)
    keep = playing(db)
    pr, pd = band_power(ref, keep), band_power(di, keep)
    if pr is None or pd is None:
        return None, None
    c = 10 * np.log10(pr + 1e-30) - 10 * np.log10(pd + 1e-30)
    return c - c.mean(), float(c.mean())


def curve_distance(a, b):
    """RMS dB difference between two tone curves."""
    import numpy as np

    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def snr_db(guitar, backing):
    import numpy as np

    g = float(np.mean(np.square(guitar, dtype=np.float64)))
    b = float(np.mean(np.square(backing, dtype=np.float64)))
    if g <= 0:
        return -math.inf
    return 10 * math.log10(g / b) if b > 0 else math.inf


# --- step 1: loading (not unit-tested; checked against the stored crops) -------------------------

def _catalog(rec):
    if "datasets-set3" in rec["catalog"].get("path", ""):
        return json.loads((HOME / "references/datasets-set3/catalog.json").read_text())
    return json.loads((PLUGIN_ROOT / "docs/validation-datasets.json").read_text())


def session(part):
    """(record, session dir, session entry, part entry) of a part's crop."""
    crop = pathlib.Path(part["crop"])
    rec = json.loads((crop / "record.json").read_text())
    cat = _catalog(rec)
    ss = [s for s in cat["sessions"] if s["source"] == rec["source"] and s["song"] == rec["song"]]
    assert len(ss) == 1, (rec["source"], rec["song"])
    s = ss[0]
    pp = [p for p in s["parts"] if p["part"] == rec["part"]]
    assert len(pp) == 1, rec["part"]
    if s.get("split") is not None:
        assert s["split"] == "development", (rec["song"], s["split"])
    return rec, pathlib.Path(cat["root"]).expanduser() / s["path"], s, pp[0]


def _fit(x, n):
    import numpy as np

    out = np.zeros(n, np.float32)
    k = min(n, len(x))
    out[:k] = x[:k]
    return out


def load_tracks(part):
    """(DI, amp track) of the whole session at 48 kHz mono, the crop builder's policy (the DI's
    length defines the session; the amp track zero-padded or cut). Checked against the crop."""
    import numpy as np

    from analysis import io

    rec, sdir, _, p = session(part)
    di = np.asarray(io.load(sdir / p["di"]).mono(), np.float32)
    ref = _fit(np.asarray(io.load(sdir / p["reference"]).mono(), np.float32), len(di))
    assert len(di) == rec["session_frames"], (len(di), rec["session_frames"])
    s, e = rec["excerpt_start_frame"], rec["excerpt_end_frame"]
    crop = pathlib.Path(part["crop"])
    dev = max(float(np.max(np.abs(di[s:e] - io.load(crop / "di.wav").mono()))),
              float(np.max(np.abs(ref[s:e] - io.load(crop / "reference.wav").mono()))))
    assert dev < 1e-5, (part["crop"], dev)
    return di, ref


def load_backing(part, n):
    """The part's backing over the whole session: the crop's declared mix tracks less its own
    amp tracks (vocals included: full mixes are the yardstick)."""
    import numpy as np

    from analysis import io

    rec, sdir, _, _ = session(part)
    own = set(rec.get("removed_own_amp_tracks", []))
    out = np.zeros(n, np.float64)
    for name in rec["included_mix_tracks"]:
        if name in own:
            continue
        out += _fit(np.asarray(io.load(sdir / name).mono(), np.float32), n)
    return out


def _bleed_flag(slug, table):
    """The bleed audit's worst flag over the crop's halves; Cambridge parts are clean (its
    finding); None when the audit has no row."""
    r = table.get(slug)
    if r is None:
        return "none (cambridge)" if slug.startswith("cambridge-") else None
    order = {"low": 0, "moderate": 1, "high": 2}
    flags = [h.get("flag") for h in r["halves"].values() if h.get("flag") in order]
    return max(flags, key=order.get) if flags else None


def scan_part(slug, part, bleed_table, with_snr=True):
    import numpy as np

    di, ref = load_tracks(part)
    db = frame_db(di)
    play = playing(db)
    lag = int(part["judge_lag"]) + LATENCY       # samples the amp track lags the DI
    L = int(SEC_S * SR)
    backing = load_backing(part, len(di)) if with_snr else None
    rows = []
    for s in grid(len(di)):
        share, halves = section_activity(play, s)
        row = {"start_s": s / SR, "active": round(share, 4), "active_halves": {k: round(v, 4) for k, v in halves.items()},
               "passes": passes(share, halves)}
        if row["passes"]:
            c, lvl = tone_curve(ref[s:s + L], di[s:s + L], lag)
            ca, _ = tone_curve(ref[s + int(HALVES["A"][0] * SR):s + int(HALVES["A"][1] * SR)],
                               di[s + int(HALVES["A"][0] * SR):s + int(HALVES["A"][1] * SR)], lag)
            cb, _ = tone_curve(ref[s + int(HALVES["B"][0] * SR):s + L], di[s + int(HALVES["B"][0] * SR):s + L], lag)
            row["tone"] = None if c is None else [round(float(v), 3) for v in c]
            row["level_db"] = None if lvl is None else round(lvl, 3)
            row["split_half_db"] = None if ca is None or cb is None else round(curve_distance(ca, cb), 4)
            if with_snr:
                row["snr_db"] = round(snr_db(ref[s:s + L], backing[s:s + L]), 3)
        rows.append(row)
    passing = [r["start_s"] for r in rows if r["passes"]]
    dis = disjoint([int(round(x * SR)) for x in passing])
    crop_start = json.loads((pathlib.Path(part["crop"]) / "record.json").read_text())["excerpt_start_s"]
    tones = [r["tone"] for r in rows if r["passes"] and r.get("tone") is not None]
    out = {"slug": slug, "band": part["band"], "gain_class": part["gain_class"], "set": part["set"],
           "session_s": round(len(di) / SR, 2), "judge_lag": part["judge_lag"], "crop_start_s": crop_start,
           "windows": len(rows), "passing": len(passing), "disjoint_starts_s": [s / SR for s in dis],
           "material_s": len(dis) * SEC_S, "bleed_flag": _bleed_flag(slug, bleed_table), "rows": rows}
    if tones:
        med = np.median(np.asarray(tones), axis=0)
        for r in rows:
            if r.get("tone") is not None:
                r["tone_dist_db"] = round(curve_distance(r["tone"], med), 4)
    return out


def sections(only=None, with_snr=True):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sections").mkdir(exist_ok=True)
    table = json.loads(BLEED.read_text())
    ps = pool()
    for slug in sorted(ps):
        if only and slug not in only:
            continue
        path = OUT / "sections" / f"{slug}.json"
        if path.exists():
            continue
        t = time.time()
        res = scan_part(slug, ps[slug], table, with_snr)
        _atomic(path, res)
        print(slug, res["passing"], len(res["disjoint_starts_s"]), f"{time.time() - t:.0f}s", flush=True)


def _atomic(path, obj):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    tmp.replace(path)


# --- step 2: does a section's search transfer? (declared in the plan) ---------------------------
N_SEARCH = 3                     # k: sections the multi-section search fits at once
N_MAX = 6                        # sections used per part: 3 searched, up to 3 held out
N_MIN = 4                        # a part needs at least one held-out section
BUDGET = 150                     # distinct settings per search (K_S's budget)
CHECKPOINTS = (25, 50, 100, 150) # settings; multi at 50 = single at 150 in renders
SEED = 20261017
REPEAT_TOL = 0.005               # |log ratio| of S re-rendered at the end of a part
STOP_HALF_WIDTH = 0.02           # stop after a batch when P's 90% half-width is at most this
MIN_BATCHES = 1
BATCH_PARTS = 12                 # bands are added whole until a batch holds at least this many parts
YIELD_TO = (r"-m learn\.rebuild_tone (render|score)\b",      # the rebuild-tone run goes first,
            r"-m learn\.rebuild_tone_train (gate|rebuild)\b")  # its CPU torch steps too
DISK_GUARD_GB = 31.0
SEARCHES = ("single1", "single2", "single3", "multi", "single1b")
# single1b (amendment 1): single1's section searched again with seed + 1, the search-path floor
# for the regrets (two searches of one section differ only by the path they took).
SEED_OF = {"single1b": SEED + 1}


AMP_FALLBACK = "pr12"           # amendment 1: when the stored menu is refused on both halves


def amp_choice(menu):
    """The amp whose best dry menu preset is closest (`flat`, the mean of the preset's finite
    halves), from the label table's stored menu (zero renders); ties by the AMPS order. When every
    stored menu score is refused (5 of the pool's parts, whose crops the judge refuses), PR12."""
    best = None
    for amp in ("pr12", "sw50r", "ac20"):
        vals = []
        for v in menu[amp].values():
            fin = [v["flat"][h] for h in "AB" if math.isfinite(v["flat"][h])]
            if fin:
                vals.append(statistics.fmean(fin))
        if vals and (best is None or min(vals) < best[1]):
            best = (amp, min(vals))
    return best[0] if best else AMP_FALLBACK


def choose_sections(slug, starts, n_max=N_MAX, n_search=N_SEARCH, seed=SEED):
    """(search sections, held sections), start seconds. From the disjoint passing sections, up
    to `n_max` spread evenly in time; roles by a seeded shuffle (seed and slug)."""
    starts = sorted(starts)
    if len(starts) > n_max:
        idx = sorted({round(i * (len(starts) - 1) / (n_max - 1)) for i in range(n_max)})
        starts = [starts[i] for i in idx]
    rng = random.Random(f"{seed}|{slug}")
    order = list(starts)
    rng.shuffle(order)
    return sorted(order[:n_search]), sorted(order[n_search:])


def batches(slugs_by_band, first, seed=SEED, size=BATCH_PARTS):
    """Batches of whole bands: step 3's parts first (`first`), then the rest; within each group
    bands in a seeded order, added until a batch holds at least `size` parts."""
    out = []
    for group in (True, False):
        bands = sorted(b for b, ss in slugs_by_band.items() if any((s in first) == group for s in ss))
        random.Random(f"{seed}|bands|{group}").shuffle(bands)
        cur = []
        for b in bands:
            cur += sorted(s for s in slugs_by_band[b] if (s in first) == group)
            if len(cur) >= size:
                out.append(cur)
                cur = []
        if cur:
            if out and len(cur) < size // 2 and all((s in first) == group for s in out[-1]):
                out[-1] += cur
            else:
                out.append(cur)
    return out


def section_score(d):
    """A section's score: the mean over its two halves of the log distance (inf if refused)."""
    if not all(d.get(h) is not None and math.isfinite(d[h]) and d[h] > 0 for h in HALVES):
        return math.inf
    return statistics.fmean(math.log(d[h]) for h in HALVES)


def held_gain(scores, s_scores, held):
    """Mean over held sections of score(x) - score(S): a log ratio against S (negative is closer)."""
    vals = [scores[j] - s_scores[j] for j in held]
    return statistics.fmean(vals) if vals and all(math.isfinite(v) for v in vals) else None


def incumbents(trace, checkpoints=CHECKPOINTS):
    """trace: [(settings so far, value, key)] in evaluation order -> {checkpoint: key of the best
    setting within the first `checkpoint` settings} (the last one if the search ended earlier)."""
    out, best = {}, None
    for n, v, k in trace:
        if best is None or v < best[0] - 1e-12:
            best = (v, k)
        for c in checkpoints:
            if n <= c:
                out[c] = best[1]
    for c in checkpoints:
        if c not in out and best is not None:
            out[c] = best[1]
    return out


def regrets(cross, own):
    """cross[(i, j)]: score of search i's final on section j; own[j] = cross[(j, j)]. ->
    {(i, j): cross - own} for i != j (how much worse i's settings do on j than j's own search)."""
    return {(i, j): v - own[j] for (i, j), v in cross.items() if i != j}


def unit_distance(dims, x, y):
    """Mean |unit difference| over the continuous dims; categorical and switch dims count 1 when
    they differ. A summary of how far apart two searched settings are."""
    vals = []
    for d in dims:
        k = (d.module, d.key)
        if k not in x or k not in y:
            continue
        if d.kind in ("cont", "log"):
            vals.append(abs(d.to_unit(x[k]) - d.to_unit(y[k])))
        else:
            vals.append(float(x[k] != y[k]))
    return statistics.fmean(vals) if vals else 0.0


# --- step 2: rendering (not unit-tested) ---------------------------------------------------------

def measure_dis(sections_audio):
    """The measure DI of each section: one EQ to the average guitar from the part's chosen
    sections together, and one gain putting them together at -22.9 LUFS (so the part's own
    dynamics between sections are kept)."""
    import numpy as np
    import pyloudnorm

    from learn import confirm_run as CR
    from learn.di_robustness import smoothed_spectrum
    from learn.direc_check import eq_to

    avg = np.load(CR.AVERAGE)
    cat = np.concatenate(list(sections_audio.values())).astype(np.float64)
    own = smoothed_spectrum(cat)
    gain = avg - (own - own.mean())
    eqd = {s: eq_to(np.asarray(x, np.float64), gain) for s, x in sections_audio.items()}
    lufs = pyloudnorm.Meter(SR).integrated_loudness(np.concatenate(list(eqd.values())))
    g = 10 ** ((-22.9 - lufs) / 20)
    return {s: x * g for s, x in eqd.items()}


def _ps():
    from learn import ks_extend as X

    return X._ps()


# Amendment 2: the cap must hold even against runners whose RENDERS list lacks this module (other
# checkouts). Any python running a learn module with a render-like or separation command counts.
FOREIGN = (r"-m learn\.(?!multi_section\b)[a-z_0-9]+ (run|render|render-new|search|probe|pregain|choose-rot|control|cross|"
           r"score-targets|score-songs|c-start|separate|identity)\b", r"-m learn\.separate\b")
MINE = r"-m learn\.multi_section run\b"
CAP = 3


def must_yield(ps=None):
    import re

    from learn import ks_extend as X

    ps = _ps() if ps is None else ps
    return [p for p, c in ps if X._is_python(c) and any(re.search(r, c) for r in YIELD_TO)]


def over_cap(ps=None, cap=CAP):
    """Foreign render or separation processes, if they and this step's workers exceed the cap
    (a separation counts as the whole machine)."""
    import re

    from learn import ks_extend as X

    ps = _ps() if ps is None else ps
    py = [(p, c) for p, c in ps if X._is_python(c)]
    foreign = [p for p, c in py if any(re.search(r, c) for r in FOREIGN)]
    mine = [p for p, c in py if re.search(MINE, c)]
    seps = [p for p, c in py if re.search(r"-m learn\.\S+ (separate|identity)\b|-m learn\.separate\b", c)]
    return foreign if (seps or len(foreign) + len(mine) > cap) else []


def clear(ps=None):
    """The runner's test before starting workers: nothing to yield to, and room for 2 workers."""
    ps = _ps() if ps is None else ps
    return not must_yield(ps) and not over_cap([*ps, (-1, "python -m learn.multi_section run"),
                                                (-2, "python -m learn.multi_section run")])


class Yield(Exception):
    pass


def disk_free_gb():
    import shutil

    return shutil.disk_usage(pathlib.Path.home()).free / 1e9


def part_dir(slug):
    return OUT / "parts" / slug


def run_part(rr, menu, slug, part, sec):
    """One part: S on every section, three single-section searches, the multi-section search,
    each incumbent at the checkpoints on every section, the S repeat check. Every render's two
    half distances go to a per-part cache file first, so a stopped worker resumes exactly."""
    import numpy as np

    from learn import knob_ceiling as K

    d = part_dir(slug)
    d.mkdir(parents=True, exist_ok=True)
    amp = amp_choice(json.loads((HOME / "learn/label-table" / slug / "menu.json").read_text()))
    start_name = K.START[part["gain_class"]][amp]
    select, s_edits = menu[amp][start_name]
    search_s, held_s = choose_sections(slug, sec["disjoint_starts_s"])
    di_full, ref_full = load_tracks(part)
    L = int(SEC_S * SR)
    secs = search_s + held_s
    raw = {s: di_full[int(s * SR):int(s * SR) + L] for s in secs}
    refs = {s: np.asarray(ref_full[int(s * SR):int(s * SR) + L], np.float64) for s in secs}
    dis = measure_dis(raw)
    del di_full, ref_full
    lag = int(part["judge_lag"])
    cache_path = d / "cache.jsonl"
    cache = {}
    if cache_path.exists():
        for line in cache_path.read_text().splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:            # a line cut by a stopped worker
                continue
            if "k" in r:
                cache[(r["k"], r["s"])] = r["d"]
    fh = cache_path.open("a")
    counts = {"renders": 0, "cached": 0}
    warm = {"done": False}

    def score(x, s):
        k = K.key(x)
        if (k, s) in cache:
            counts["cached"] += 1
            return section_score(cache[(k, s)])
        ps = _ps()
        if must_yield(ps) or over_cap(ps):
            raise Yield()
        if not warm["done"]:
            rr.render(dis[s].astype(np.float32), select, s_edits)
            warm["done"] = True
            fh.write(json.dumps({"warmup": s}) + "\n")
            fh.flush()
        y = rr.render(dis[s].astype(np.float32), select, x)
        jd = K.judge(refs[s], y, dis[s], lag)
        dd = {h: (None if not math.isfinite(v) else v) for h, v in jd.items()}
        cache[(k, s)] = dd
        fh.write(json.dumps({"k": k, "s": s, "d": dd}) + "\n")
        fh.flush()
        counts["renders"] += 1
        return section_score(dd)

    try:
        s_scores = {s: score(s_edits, s) for s in secs}
        kept = [s for s in secs if math.isfinite(s_scores[s])]
        search_s = [s for s in search_s if s in kept]
        held_s = [s for s in held_s if s in kept]
        res = {"slug": slug, "band": part["band"], "gain_class": part["gain_class"], "amp": amp, "start": start_name,
               "search_sections": search_s, "held_sections": held_s, "dropped_sections": [s for s in secs if s not in kept],
               "s_scores": {str(s): s_scores[s] for s in kept}}
        if len(search_s) < N_SEARCH or not held_s:
            res["skipped"] = "a search or held section is refused for S"
            _atomic(d / "result.json", res)
            return res
        dims = K.space(amp, s_edits)
        settings = {K.key(s_edits): dict(s_edits)}
        runs = {}
        for name in SEARCHES:
            objective = search_s if name == "multi" else [search_s[int(name[6]) - 1]]
            trace = []

            def f(x, objective=objective, trace=trace):
                v = statistics.fmean(score(x, s) for s in objective)
                k = K.key(x)
                settings.setdefault(k, dict(x))
                trace.append((len(trace) + 1, v, k))
                return v

            x, best, _, stages = K.knob_search(dims, dict(s_edits), f, BUDGET, SEED_OF.get(name, SEED))
            inc = incumbents(trace)
            runs[name] = {"objective": objective, "settings": len(trace), "final": K.key(x), "best": best,
                          "incumbents": {str(c): k for c, k in inc.items()}, "stages": stages,
                          "changed": {f"{m}/{kk}": v for (m, kk), v in x.items() if s_edits.get((m, kk)) != v}}
        # every incumbent at every checkpoint, on every kept section
        table = {}
        for name, r in runs.items():
            for c, k in r["incumbents"].items():
                table.setdefault(name, {})[c] = {str(s): score(settings[k], s) for s in kept}
        # the S repeat check: S's first section rendered again, compared with its stored value
        k0 = K.key(s_edits)
        first = cache.pop((k0, kept[0]))
        again = score(s_edits, kept[0])
        dev = abs(again - section_score(first))
        fh.flush()
        renders = sum(1 for line in cache_path.read_text().splitlines() if line.strip())
        res.update(runs=runs, table=table, repeat_dev=dev, renders=renders, renders_this_session=counts["renders"],
                   distances={f"{a}|{b}": unit_distance(dims, settings[runs[a]["final"]], settings[runs[b]["final"]])
                              for i, a in enumerate(SEARCHES) for b in SEARCHES[i + 1:]})
        if dev > REPEAT_TOL:
            res["repeat_failed"] = True
        _atomic(d / "result.json", res)
        return res
    finally:
        fh.close()


def plan_batches():
    ps = pool()
    secs = {s: json.loads((OUT / "sections" / f"{s}.json").read_text()) for s in ps}
    eligible = {s for s in ps if len(secs[s]["disjoint_starts_s"]) >= N_MIN}
    by_band = {}
    for s in sorted(eligible):
        by_band.setdefault(ps[s]["band"], []).append(s)
    return batches(by_band, set(step3_parts())), ps, secs


def run(worker, batch_no):
    from learn import knob_ceiling as K
    from learn import local_objective as LO

    bs, ps, secs = plan_batches()
    todo = bs[batch_no][worker[0]::worker[1]]
    rr = None
    try:
        for slug in todo:
            if (part_dir(slug) / "result.json").exists():
                continue
            if must_yield():
                print("YIELD", flush=True)
                sys.exit(3)
            LO._wait_cap()
            if disk_free_gb() < DISK_GUARD_GB:
                print(f"DISK GUARD {disk_free_gb():.1f} GB", flush=True)
                sys.exit(4)
            if rr is None:
                rr = K.Renderer()
                menu = rr.menu()
            t = time.time()
            try:
                res = run_part(rr, menu, slug, ps[slug], secs[slug])
            except Yield:
                print("YIELD", flush=True)
                sys.exit(3)
            print(slug, res.get("amp"), res.get("renders"), f"{time.time() - t:.0f}s",
                  "REPEAT FAILED" if res.get("repeat_failed") else "", flush=True)
    finally:
        if rr is not None:
            rr.close()
    print(f"WORKER DONE batch {batch_no} {worker[0]}/{worker[1]}", flush=True)


# --- step 2: readout (zero renders) ---------------------------------------------------------------

def _bw(rows):
    from learn import song_readout as SR_

    return SR_.bw_stats(rows)


def _fin(*xs):
    return all(x is not None and math.isfinite(x) for x in xs)


def _mean_or_none(vals):
    vals = list(vals)
    return statistics.fmean(vals) if vals and _fin(*vals) else None


def part_readout(res, cp="150"):
    """Per-part numbers from a result.json (None where not computable: any refused score)."""
    t, s0 = res["table"], {s: v for s, v in res["s_scores"].items()}
    held = [str(s) for s in res["held_sections"]]
    search = [str(s) for s in res["search_sections"]]

    def hg(name, c=cp, where=held):
        return held_gain(t[name][c], s0, where) if name in t else None

    singles = [hg(f"single{i}") for i in (1, 2, 3)]
    out = {"multi": hg("multi"), "single_mean": statistics.fmean(singles) if None not in singles else None,
           "multi_50": hg("multi", "50")}
    out["P"] = None if out["multi"] is None or out["single_mean"] is None else out["multi"] - out["single_mean"]
    out["P_equal_renders"] = (None if out["multi_50"] is None or out["single_mean"] is None
                              else out["multi_50"] - out["single_mean"])
    out["single_own"] = _mean_or_none(t[f"single{i}"][cp][search[i - 1]] - s0[search[i - 1]] for i in (1, 2, 3))
    cross = {(i, j): t[f"single{i}"][cp][search[j - 1]] for i in (1, 2, 3) for j in (1, 2, 3)}
    rg = regrets(cross, {j: cross[(j, j)] for j in (1, 2, 3)})
    ok = _fin(*cross.values())
    out["regret_mean"] = statistics.fmean(rg.values()) if ok else None
    out["regret_max"] = max(rg.values()) if ok else None
    out["transfer_worse_than_S"] = (sum(cross[(i, j)] > s0[search[j - 1]] for (i, j) in rg) / len(rg)) if ok else None
    out["single_other_search"] = (statistics.fmean(cross[(i, j)] - s0[search[j - 1]] for (i, j) in rg)
                                  if ok else None)
    out["multi_own"] = _mean_or_none(t["multi"][cp][s] - s0[s] for s in search)
    # amendment 1: the search-path floor. single1b searched s1 again with another seed; how far its
    # settings land from single1's on s1 (both ways, so the mean is the absolute gap), and its
    # regrets on s2, s3 beside single1's (how much the regrets move with the path alone).
    if "single1b" in t:
        a, b = t["single1"][cp][search[0]], t["single1b"][cp][search[0]]
        out["seed_gap_own"] = abs(a - b) if _fin(a, b) else None
        r1 = [cross[(1, j)] - cross[(j, j)] for j in (2, 3)]
        r1b = [t["single1b"][cp][search[j - 1]] - cross[(j, j)] for j in (2, 3)]
        out["seed_regret_change"] = (statistics.fmean(abs(x - y) for x, y in zip(r1, r1b))
                                     if _fin(*r1, *r1b) else None)
        out["single1b_held_minus_single1"] = (None if hg("single1b") is None or singles[0] is None
                                              else hg("single1b") - singles[0])
    return out


def held_gaps(res):
    """Seconds from each held section to the nearest search section (descriptive)."""
    return [min(abs(h - s) for s in res["search_sections"]) for h in res["held_sections"]]


ROWS = {"all": lambda r, sec: True,
        "no_high_bleed": lambda r, sec: sec.get("bleed_flag") != "high",
        "no_moderate_or_high_bleed": lambda r, sec: sec.get("bleed_flag") not in ("high", "moderate"),
        "cambridge": lambda r, sec: r["slug"].startswith("cambridge-"),
        "clean": lambda r, sec: r["gain_class"] == "clean",
        "crunch": lambda r, sec: r["gain_class"] == "crunch"}
KEYS = ("P", "P_equal_renders", "multi", "single_mean", "single_own", "single_other_search", "multi_own",
        "regret_mean", "regret_max", "transfer_worse_than_S", "seed_gap_own", "seed_regret_change",
        "single1b_held_minus_single1")


def spearman(xs, ys):
    from scipy import stats

    if len(xs) < 3:
        return None
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    return float(stats.spearmanr(xs, ys).correlation)


def tone_pairs(res, sec, cp="150"):
    """[(tone-curve distance, symmetric regret)] over the part's search-section pairs: does the
    zero-render tone curve predict where one section's settings fail on another?"""
    t, search = res["table"], [str(s) for s in res["search_sections"]]
    tone = {str(x["start_s"]): x.get("tone") for x in sec["rows"]}
    cross = {(i, j): t[f"single{i}"][cp][search[j - 1]] for i in (1, 2, 3) for j in (1, 2, 3)}
    rg = regrets(cross, {j: cross[(j, j)] for j in (1, 2, 3)})
    out = []
    for i, j in ((1, 2), (1, 3), (2, 3)):
        a, b = tone.get(search[i - 1]), tone.get(search[j - 1])
        if a is not None and b is not None:
            out.append((curve_distance(a, b), (rg[(i, j)] + rg[(j, i)]) / 2))
    return out


def report():
    rows, dropped = {}, {}
    for d in sorted((OUT / "parts").glob("*/result.json")):
        r = json.loads(d.read_text())
        if "skipped" in r or "table" not in r:
            dropped[r["slug"]] = r.get("skipped", "incomplete")
            continue
        if r.get("repeat_failed"):
            dropped[r["slug"]] = f"S repeat moved {r['repeat_dev']:.4f}"
            continue
        sec = json.loads((OUT / "sections" / f"{r['slug']}.json").read_text())
        rows[r["slug"]] = (r, part_readout(r), sec)
    out = {"parts": len(rows), "bands": len({r["band"] for r, _, _ in rows.values()}),
           "renders": sum(r["renders"] for r, _, _ in rows.values()), "dropped": dropped}
    for name, keep in ROWS.items():
        sel = [(r, pr) for r, pr, sec in rows.values() if keep(r, sec)]
        out[name] = {k: _bw([(r["band"], pr[k]) for r, pr in sel if pr.get(k) is not None]) for k in KEYS}
    for cp in map(str, CHECKPOINTS):
        vals = [(r["band"], part_readout(r, cp)) for r, _, _ in rows.values()]
        out[f"curve_{cp}"] = {k: _bw([(b, v[k]) for b, v in vals if v[k] is not None])
                              for k in ("multi", "single_mean", "P", "P_equal_renders")}
    out["tone_vs_regret"] = {}
    for name in ("all", "cambridge"):
        per = [tone_pairs(r, sec) for r, _, sec in rows.values() if ROWS[name](r, sec)]
        pairs = [p for pp in per for p in pp]
        within = [(a - statistics.fmean(x for x, _ in pp), b - statistics.fmean(y for _, y in pp))
                  for pp in per if len(pp) >= 2 for a, b in pp]
        out["tone_vs_regret"][name] = {
            "pairs": len(pairs), "spearman": spearman([a for a, _ in pairs], [b for _, b in pairs]),
            "spearman_within_part": spearman([a for a, _ in within], [b for _, b in within])}
    out["P_none"] = sorted(s for s, (_, pr, _) in rows.items() if pr["P"] is None)
    gaps = [g for r, _, _ in rows.values() for g in held_gaps(r)]
    out["held_gap_s"] = {"n": len(gaps), "min": min(gaps) if gaps else None,
                         "median": statistics.median(gaps) if gaps else None,
                         "le_10s": sum(g <= 10 for g in gaps)}
    out["per_part"] = {s: pr for s, (_, pr, _) in rows.items()}
    _atomic(OUT / "report.json", out)
    return out


def decide(batch_no):
    """After a batch: STOP when P's 90% half-width is at most STOP_HALF_WIDTH (and at least
    MIN_BATCHES batches ran) or the pool is spent; else CONTINUE."""
    bs, _, _ = plan_batches()
    out = report()
    P = out["all"]["P"]
    hw = None if P["lo90"] is None else (P["hi90"] - P["lo90"]) / 2
    stop = batch_no + 1 >= len(bs) or (batch_no + 1 >= MIN_BATCHES and hw is not None and hw <= STOP_HALF_WIDTH)
    print(f"batch {batch_no}: P {P['band_weighted_mean']} half-width {hw} -> {'STOP' if stop else 'CONTINUE'}",
          flush=True)
    return bool(stop)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("sections")
    a.add_argument("--only", nargs="*")
    a.add_argument("--no-snr", action="store_true")
    a = sub.add_parser("run")
    a.add_argument("--worker", default="0/1")
    a.add_argument("--batch", type=int, required=True)
    sub.add_parser("report")
    a = sub.add_parser("decide")
    a.add_argument("--batch", type=int, required=True)
    sub.add_parser("batches")
    sub.add_parser("clear")
    args = ap.parse_args(argv)
    if args.cmd == "sections":
        sections(args.only, not args.no_snr)
    elif args.cmd == "run":
        i, n = map(int, args.worker.split("/"))
        run((i, n), args.batch)
    elif args.cmd == "report":
        print(json.dumps({k: v for k, v in report().items() if k != "per_part"}, indent=1, default=str))
    elif args.cmd == "decide":
        print("DECISION", "STOP" if decide(args.batch) else "CONTINUE", flush=True)
    elif args.cmd == "clear":
        sys.exit(0 if clear() else 10)      # 10: not clear (any other code is a failure)
    elif args.cmd == "batches":
        bs, ps, _ = plan_batches()
        for i, b in enumerate(bs):
            print(i, len(b), len({ps[s]["band"] for s in b}), b)


if __name__ == "__main__":
    main()
