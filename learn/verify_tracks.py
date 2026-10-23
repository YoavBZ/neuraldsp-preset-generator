"""The trusted-data plan's verification standard and stage T0 (`docs/trusted-data-strategy-plan.md`, approved
2026-10-23 with its recorded decisions; the thresholds and their calibration are in
`docs/trusted-data-t0-design.md`). Development data only: sets 1-3's label-table parts, part C's pool and
V_sep; nothing from sets 4-6, Guitar-TECHS P3 or a reservation in `dev-test-ledger.json` is opened.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    $MAIN -u -m learn.verify_tracks negatives       # calibration's Morgan cab-off renders: 6 (one process, isolate, primed)
    $MAIN -m learn.verify_tracks calibrate          # CALIBRATION OK | FAIL (zero renders; reads the negatives' renders)
    $MAIN -m learn.verify_tracks targets            # A1-A6 on every amp-track target in use (needs CALIBRATION OK)
    $MAIN -m learn.verify_tracks dis --shard k/3    # D1-D3 on every DI in use (pool, V_sep, the crops' measure DIs)
    $MAIN -m learn.verify_tracks inject-strict      # the take estimator at -35 and -40 dB (a stricter stem floor?)
    $MAIN -m learn.verify_tracks stem-scan --shard k/3   # every guitar track's take in every non-guitar stem
    $MAIN -m learn.verify_tracks lists [--ear EXPORT.json ...]   # the trusted lists, the ear's queue, the level prior
    $MAIN -m learn.verify_tracks reread             # zero-render re-reads of the results that rest on failing parts

**The standard** (plan (a)), per judge half of a crop (A 1.0-5.5 s, B 5.5-10.0 s), the crop's `reference.wav`
against its `di.wav`:
- **A1, mic delay:** GCC-PHAT lag, DI to target, over 80 Hz-4 kHz (calibration: the full band reads 0 ms on 9 of
  the 18 known amps, whose amp tracks carry a zero-lag direct path above 4 kHz; the bleed audit's stored
  `di_lag_ms`, read at 24 kHz over +-40 s, agrees with the band-limited reading and is shown beside). Pass
  0.1 <= |lag| <= 30 ms; a negative lag goes to the ear.
- **A2, cab roll-off:** H1 = S_xy/S_xx (Welch, 4096, Hann), bins with coherence >= 0.5: the median |H| over 6-10 kHz
  at least `A2_DROP_DB` under the median over 1-3 kHz. A half decides only with >= `A2_MIN_BINS` coherent bins in
  both bands; with fewer, the half goes to the ear. A part fails if a deciding half fails, passes if a half
  passes and none fails, else goes to the ear.
- **A3, linear copy:** the residual of the best linear filter (least squares, exact covariance method, 24 kHz,
  taps -5..+60 ms around the A1 lag, ridge 1e-7 of the mean diagonal) fitted on one half and applied to the other,
  both ways; pass when both residuals are above -40 dB (calibration: EQ'd copies read -80 to -110 dB, amps -1 to
  -32 dB).
- **A4, not a copy:** peak |correlation| (+-50 ms) of the target with every DI of its session below 0.95, and no
  session DI file with the target file's sha256.
- **A5, same take** (the cleaning plan's rule, `crop_match2.py`'s measures): DI play share >= 0.5, and chroma
  >= 0.8 or onset correlation >= 0.35.
- **A6, clean:** the bleed audit's bleed under -30 dB (`bleed-table.json`); and, where the part is read in a mix
  (stage F, V-real), no other take of the part in the mix: a pitch-confirmed same-part track (the cleaning plan's
  `same_part` rule on the crop window) at or above -30 dB of the target.
- **DIs:** D1, the DI passes A1 and does not fail A2 against its own amp track, per section; D2, no clipping or
  drop-outs on the window and no hum (part A's flags; the user's decision 2 excludes hummy measure DIs), hiss and
  bleed shown; D3, not a line out or processor output by name. DI-only parts take D2-D3 and the ear.

**The rule:** a measured fail is excluded (decision 2). A target is trusted only when it passes the measures and the
user has heard it clean (data-review-1, both halves) and, where A1 or A2 went to the ear, heard it as an amp (the
target-vs-DI page). Quicksand ElecGtr2 and Today's The Day ElecGtr07 stay excluded until the user's ear rules on
them. Thresholds move only to separate the calibration's known cases (`THRESHOLD_MOVES`).

The pure parts are unit-tested (`tests/test_verify_tracks.py`); the commands that read audio or render are not,
like the other step modules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import re
import statistics
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
OUT = HOME / "learn/trusted-data"
PLAN = "docs/trusted-data-strategy-plan.md"
DESIGN = "docs/trusted-data-t0-design.md"
LEDGER_ID = "trusted-data"
LABEL_TABLE = PLUGIN_ROOT / "docs/label-table-parts.json"
BLEED_TABLE = PLUGIN_ROOT / "docs/audits/bleed-2026-10-16/bleed-table.json"
CAT12 = PLUGIN_ROOT / "docs/validation-datasets.json"
CAT3 = HOME / "references/datasets-set3/catalog.json"
SR = 48_000
HALVES = {"A": (1.0, 5.5), "B": (5.5, 10.0)}
CROP_S = 10.0
DISK_GUARD_GB = 31.0

# --- A1: mic delay ---------------------------------------------------------------------------------------------
LAG_BAND_HZ = (80.0, 4000.0)
LAG_SEARCH_MS = 50.0
LAG_MIN_MS, LAG_MAX_MS = 0.1, 30.0
A1_PROM_MIN = 12.0                    # a lag is read only when its GCC peak stands this far over the median (calibration)

# --- A2: cab roll-off ------------------------------------------------------------------------------------------
A2_NPERSEG = 4096
A2_COH_MIN = 0.5
A2_LO_HZ = (1000.0, 3000.0)
A2_HI_HZ = (6000.0, 10000.0)
A2_MIN_BINS = 17                      # 5% of the 342 bins over 6-10 kHz at 48 kHz / 4096 (the plan gave no number)
A2_DROP_DB = 3.3                      # moved from the plan's 12 dB by calibration (THRESHOLD_MOVES)

# --- A3: linear copy -------------------------------------------------------------------------------------------
A3_SR = 24_000
A3_PRE_MS, A3_POST_MS = 5.0, 60.0
A3_RIDGE = 1e-7
A3_MAX_DB = -40.0                     # a residual above this passes (the target is not an EQ'd copy)

# --- A4: not a copy --------------------------------------------------------------------------------------------
A4_MAX_CORR = 0.95
A4_LAG_MS = 50.0

# --- A5: same take (the cleaning plan's rule) ------------------------------------------------------------------
A5_PLAY_MIN = 0.5
A5_CHROMA_MIN = 0.8
A5_ONSET_MIN = 0.35

# A1-A3 read a half only where the DI plays on at least this share of its frames (a measurement gate, not A5's rule)
MEASURE_PLAY_MIN = 0.25

# --- A6: clean -------------------------------------------------------------------------------------------------
A6_BLEED_DB = -30.0
A6_TAKE_DB = -30.0

# --- D4: the DI is unprocessed (user, 2026-10-23: sitting 1 of data-review-1 judged the crops' DIs) --------------
D4_FRAME_S = 0.1                      # frames for the crest factor and the brightness slope
D4_PLAY_DB = 30.0                     # frames within this of the loudest
D4_CREST_DB = 8.4                     # a median frame crest under this reads as driven or compressed
D4_SLOPE_MIN = -0.2                   # dB of (3-8 kHz over 0.1-1.5 kHz) per dB of level: under this, brightness does
                                      # not rise with picking strength (a saturating stage)

# --- D3: by name -----------------------------------------------------------------------------------------------
D3_RE = re.compile(r"pedal\s*board|line\s*out|lineout|\bfx\b|\bsim\b|kemper|\baxe\b|helix|\bpod\b|processed|"
                   r"re-?amp|effects?\b|\bwet\b", re.I)

# The plan's thresholds that calibration moved, toward keeping the known amps (plan (a): "each move is recorded").
THRESHOLD_MOVES = (
    {"threshold": "A2_DROP_DB", "plan": 12.0, "now": A2_DROP_DB,
     "why": "the known amps colour-me-red elecgtr03 (half A, 6.2 dB over 46 coherent bins) and Signs ElecGtr2 (half A, "
            "10.3 dB over 27) read under 12 dB; the highest known fail is Prodigal ElecGtr5 half B at 0.4 dB (255 bins) "
            "and the DI copy reads 0.0. Set at the midpoint of 0.4 and 6.2; the cab-off negative must read under it, "
            "else the threshold moves to the midpoint of the new closest pair (recorded)"},
    {"threshold": "A2_MIN_BINS", "plan": None, "now": A2_MIN_BINS,
     "why": "the plan sends 'too few coherent bins above 6 kHz' to the ear without a number; 5% of the band. "
            "Quicksand ElecGtr2 (12 and 10 bins, -2.5 and -3.9 dB) falls under it and goes to the ear"},
    {"threshold": "A1_PROM_MIN", "plan": None, "now": A1_PROM_MIN,
     "why": "a lag is read only where the GCC peak stands out: the 18 known amps' halves read prominence 24-279, "
            "the unreadable high-gain DI/amp pairs 4.4-6.7; under it A1 goes to the ear (no known case moves)"},
    {"threshold": "D4 (new, user 2026-10-23)", "plan": None, "now": f"crest < {D4_CREST_DB} dB or slope < {D4_SLOPE_MIN}",
     "why": "set on the user's 35 heard crop DIs (sitting 1): the OR rule that best separates heard-processed from "
            "heard-clean (16 of 17 processed caught; 4 of 18 clean flagged: Drag Me Down 4, Quicksand 2, Signs 2, "
            "colour-me-red 03). The ear overrides it both ways on heard DIs"},
    {"threshold": "A1 band", "plan": "full band (the bleed audit's di_lag_ms)", "now": f"{LAG_BAND_HZ[0]:.0f}-{LAG_BAND_HZ[1]:.0f} Hz",
     "why": "on the 48 kHz crops the full-band GCC-PHAT reads 0 ms on 9 of the 18 known amps (a zero-lag path above "
            "4 kHz); the band-limited lag agrees with the stored di_lag_ms (read at 24 kHz)"},
)

# --- calibration ---------------------------------------------------------------------------------------------
# The 18 targets heard clean on data-review-1 and measured as amps on the target-vs-DI check (2026-10-23); the two
# Prodigal parts heard clean but measured as processed DIs with no cab.
KNOWN_AMPS = (
    "cambridge-Drag_Me_Down-ElecGtr4", "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr1",
    "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr2", "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr3",
    "cambridge-Passing_Ships-ElecGtr4", "cambridge-Quicksand-ElecGtr2", "cambridge-Signs-ElecGtr2",
    "cambridge-Today's_The_Day-ElecGtr07", "cambridge-colour-me-red-elecgtr02", "cambridge-colour-me-red-elecgtr03",
    "cambridge-get-out-of-bed-elecgtr2", "cambridge-let-s-dance-elecgtr3", "cambridge-let-s-dance-elecgtr4",
    "cambridge-magilla-elecgtr1", "cambridge-magilla-elecgtr1dt", "cambridge-wickerman-elecgtr3",
    "telefunken-Blind_Spots-GTR", "telefunken-Sculptor's_Request-GTR_2")
KNOWN_FAILS = ("cambridge-Prodigal-ElecGtr3", "cambridge-Prodigal-ElecGtr5")
# The constructed negatives' DIs: one whose HF stays coherent through an amp (Passing Ships ElecGtr4) and one clean
# part whose amp track is incoherent above 6 kHz (magilla elecgtr1).
NEG_SOURCES = ("cambridge-Passing_Ships-ElecGtr4", "cambridge-magilla-elecgtr1")
NEG_KINDS = ("copy", "eq", "cab_off_clean", "cab_off_crunch")
NEG_DECLARED = {"copy": "the DI itself", "eq": "the DI through a cab-like linear EQ, delayed 1.5 ms",
                "cab_off_clean": "the DI through Morgan PR12 (clean start), cab section off",
                "cab_off_crunch": "beside: the DI through Morgan PR12 (crunch start), cab section off"}
NEG_MUST_FAIL = {"copy": ("A1", "A3", "A4"), "eq": ("A3",), "cab_off_clean": ("A2",)}   # any one of these must fail
NEG_AMP, NEG_LEVEL_LUFS = "pr12", -22.9
NEG_EQ = {"band_hz": (80.0, 5000.0), "order": 4, "peak_hz": 2000.0, "peak_q": 1.5, "peak_gain": 1.0, "delay_ms": 1.5,
          "gain": 0.5}
EAR_DISPUTED = ("cambridge-Quicksand-ElecGtr2", "cambridge-Today's_The_Day-ElecGtr07")

# --- the stem scan ---------------------------------------------------------------------------------------------
STEM_TAKE_DB = -30.0                  # a stem passes when every guitar track of its session reads under this
STRICT_LEVELS = (-35.0, -40.0)
STRICT_DETECT_TOL = 3.0               # an injected take at L must read at least L - 3 dB
STRICT_BASE_MARGIN = 5.0              # ... and the uninjected track under L - 5 dB
REMOVED = "Kimock and Swatkins stay out of K (recorded decision, 2026-10-23)"
K_OUT_BANDS = ("John Morgan Kimock", "Swatkins")
EGGY = "Eggy"


# --- pure: statuses ----------------------------------------------------------------------------------------------

def a1_status(lag_ms, lo=LAG_MIN_MS, hi=LAG_MAX_MS, prominence=None, prom_min=A1_PROM_MIN):
    """'pass', 'fail' or 'ear' of one A1 lag: a negative lag (a recording offset) and an unreadable one (a GCC peak
    under `prom_min` over the median: no linear path to time) go to the ear."""
    if prominence is not None and prominence < prom_min:
        return "ear"
    if lag_ms is None or not math.isfinite(lag_ms):
        return "fail"
    if not lo <= abs(lag_ms) <= hi:
        return "fail"
    return "ear" if lag_ms < 0 else "pass"


def a2_half_status(drop_db, n_lo, n_hi, min_bins=A2_MIN_BINS, thr=A2_DROP_DB):
    """One half's A2: 'ear' with too few coherent bins in either band, else pass/fail on the drop."""
    if drop_db is None or n_lo < min_bins or n_hi < min_bins:
        return "ear"
    return "pass" if drop_db >= thr else "fail"


def combine_part(statuses):
    """A part's status from its halves' (or sections') under the strict rule: fail if any fails (or none was
    read), pass if all pass, else ear."""
    s = [x for x in statuses if x is not None]
    if not s or "fail" in s:
        return "fail"
    return "pass" if all(x == "pass" for x in s) else "ear"


def a2_part(statuses):
    """A2 over a part's halves: fail if a deciding half fails, pass if a half passes and none fails, else ear."""
    s = [x for x in statuses if x is not None]
    if "fail" in s:
        return "fail"
    return "pass" if "pass" in s else "ear"


def a3_status(residuals_db, thr=A3_MAX_DB):
    """Pass when every cross-half residual is above `thr` (no direction finds an EQ'd copy)."""
    r = [v for v in residuals_db if v is not None]
    if not r:
        return "fail"
    return "pass" if min(r) > thr else "fail"


def a4_status(max_corr, same_hash, thr=A4_MAX_CORR):
    if same_hash:
        return "fail"
    return "pass" if max_corr is None or max_corr < thr else "fail"


def a5_half_status(play_share, chroma, onset, play_min=A5_PLAY_MIN, cmin=A5_CHROMA_MIN, omin=A5_ONSET_MIN):
    if play_share is None or play_share < play_min:
        return "fail"
    c_ok = chroma is not None and chroma >= cmin
    o_ok = onset is not None and onset >= omin
    return "pass" if c_ok or o_ok else "fail"


def a6_half_status(bleed_half, thr=A6_BLEED_DB):
    """The bleed audit's half: under `thr` passes; a silent half, a missing reading or more bleed fails."""
    if not bleed_half or bleed_half.get("flag") == "silent":
        return "fail"
    b = bleed_half.get("bleed_db")
    return "pass" if isinstance(b, (int, float)) and b < thr else "fail"


def a6_mix_status(take_levels_db, thr=A6_TAKE_DB):
    """No other take of the part in the mix: every pitch-confirmed same-part track under `thr` (dB of the target)."""
    return "pass" if all(v is None or v < thr for v in take_levels_db) else "fail"


def d3_status(name):
    return "fail" if D3_RE.search(pathlib.PurePosixPath(str(name)).stem) else "pass"


def d2_status(flags, hum_suspect=False):
    """Part A's flags on the window: clipping, drop-outs and hum exclude, and so does part A's hum-suspect list
    (decision 2: hummy measure DIs out); hiss and bleed are shown."""
    return "fail" if hum_suspect or set(flags or ()) & {"clipping", "dropout", "hum"} else "pass"


def target_verdict(st, ear_clean, ear_amp, disputed=False, in_mix=False):
    """A target's standing. st: {measure: status}; ear_clean: True/False/None (both halves heard clean on
    data-review-1); ear_amp: True/False/None (heard as an amp on the target-vs-DI page).
    -> (verdict, reasons): 'trusted', 'excluded' (a measured fail, or the ear said no) or 'pending ear'."""
    need = ["A1", "A2", "A3", "A4", "A5", "A6"] + (["A6mix"] if in_mix else [])
    fails = [m for m in need if st.get(m) == "fail" or st.get(m) is None]
    if fails:
        return "excluded", [f"{m} fails" for m in fails]
    why = []
    if ear_clean is False:
        return "excluded", ["heard not clean"]
    if ear_amp is False:
        return "excluded", ["heard as not an amp"]
    ear = [m for m in need if st.get(m) == "ear"]
    if ear and ear_amp is not True:
        why.append(f"{', '.join(ear)} to the ear (amp or not)")
    if ear_clean is None:
        why.append("not yet heard (clean or not)")
    if disputed:
        why.append("user-disputed: excluded until the user's ear rules")
    return ("pending ear", why) if why else ("trusted", [])


def d1_status(halves, prom_min=A1_PROM_MIN, min_bins=A2_MIN_BINS, thr=A2_DROP_DB):
    """D1 over a DI's sections (a chain property, read robustly): A1 on the median of its readable lags (GCC
    prominence >= prom_min), A2 on the median drop of its deciding halves; 'ear' where nothing is readable.
    halves: [{"lag_ms", "lag_prominence", "a2": {...}}]. -> {"status", "A1", "A2", "lag_ms", "drop_db", "n"}."""
    lags = [h["lag_ms"] for h in halves if (h.get("lag_prominence") or 0) >= prom_min]
    drops = [h["a2"]["drop_db"] for h in halves
             if a2_half_status(h["a2"]["drop_db"], h["a2"]["n_lo"], h["a2"]["n_hi"], min_bins, thr) != "ear"]
    lag = statistics.median(lags) if lags else None
    drop = statistics.median(drops) if drops else None
    a1 = a1_status(lag) if lags else "ear"
    a2 = "ear" if drop is None else ("pass" if drop >= thr else "fail")
    status = "fail" if "fail" in (a1, a2) else ("pass" if (a1, a2) == ("pass", "pass") else "ear")
    return {"status": status, "A1": a1, "A2": a2, "lag_ms": lag, "drop_db": drop, "n_lags": len(lags),
            "n_drops": len(drops)}


def di_verdict(st):
    """A DI's standing: excluded on a measured fail; D1 to the ear (a negative lag, or A2 undecided) keeps the DI
    in use and queues it for the ear (not a measured fail); DI-only parts (no D1) likewise."""
    fails = [m for m in ("D1", "D2", "D3", "D4") if st.get(m) == "fail"]
    if fails:
        return "excluded", [f"{m} fails" for m in fails]
    q = [m for m in ("D1",) if st.get(m) in ("ear", None)]
    return "trusted", ([f"{m} {'to the ear' if st.get(m) == 'ear' else 'not measurable (DI-only)'}" for m in q])


def d4_status(crest_db, bright_slope, crest_min=D4_CREST_DB, slope_min=D4_SLOPE_MIN):
    """The DI-is-unprocessed check: 'fail' (reads as processed: drive or compression) when the median frame crest
    factor is under crest_min or the brightness does not rise with level; None readings fail closed."""
    if crest_db is None or bright_slope is None:
        return "fail"
    return "fail" if crest_db < crest_min or bright_slope < slope_min else "pass"


def ear_di_verdict(halves):
    """The user's ear on a crop's DI (data-review-1, sitting 1: the DI clip): True when every heard half is 'clean',
    False when any half is heard otherwise (processed, an amp, another guitar), None when not heard."""
    vs = [v for v in halves.values() if v is not None]
    if not vs:
        return None
    return all(v == "clean" for v in vs)


def calibration_verdict(rows, must_fail=NEG_MUST_FAIL):
    """rows: [{"name", "kind" ('known', 'fail', or a negative kind), "status": {A1..A4: status}}].
    OK iff every known amp fails none of A1-A4, every known fail fails at least one, and every declared negative
    fails one of its listed measures (negatives outside `must_fail` are beside). -> (verdict, problems)."""
    probs = []
    seen = {"known": 0, "fail": 0}
    neg_seen = set()
    for r in rows:
        st = r["status"]
        failed = [m for m in ("A1", "A2", "A3", "A4") if st.get(m) == "fail"]
        if r["kind"] == "known":
            seen["known"] += 1
            if failed:
                probs.append(f"known amp {r['name']} fails {failed}")
        elif r["kind"] == "fail":
            seen["fail"] += 1
            if not failed:
                probs.append(f"known fail {r['name']} fails nothing")
        elif r["kind"] in must_fail:
            neg_seen.add(r["kind"])
            if not set(failed) & set(must_fail[r["kind"]]):
                probs.append(f"negative {r['name']} ({r['kind']}) fails none of {list(must_fail[r['kind']])}")
    if seen["known"] != len(KNOWN_AMPS) or seen["fail"] != len(KNOWN_FAILS):
        probs.append(f"calibration read {seen['known']} known amps and {seen['fail']} known fails")
    for k in must_fail:
        if k not in neg_seen:
            probs.append(f"no {k} negative was read")
    return ("OK" if not probs else "FAIL"), probs


def margins(rows, measure, value_of, keep):
    """The closest known amp and the closest negative or known fail to a threshold: (min over known, max over
    the rest) of value_of(row) where defined. Descriptive (the calibration record)."""
    k = [value_of(r) for r in rows if r["kind"] == "known" and value_of(r) is not None]
    n = [value_of(r) for r in rows if r["kind"] != "known" and keep(r) and value_of(r) is not None]
    return {"measure": measure, "known_min": min(k) if k else None, "others_max": max(n) if n else None}


# --- pure: signals -----------------------------------------------------------------------------------------------

def gcc_lag_ms(x, y, sr, band=LAG_BAND_HZ, max_ms=LAG_SEARCH_MS):
    """GCC-PHAT lag of y against x (positive: y later), band-limited. -> (lag ms, peak over median)."""
    import numpy as np

    n = 1 << int(math.ceil(math.log2(len(x) + len(y))))
    R = np.fft.rfft(y, n) * np.conj(np.fft.rfft(x, n))
    R /= np.abs(R) + 1e-12
    if band is not None:
        f = np.fft.rfftfreq(n, 1 / sr)
        R *= (f >= band[0]) & (f < band[1])
    r = np.fft.irfft(R, n)
    m = int(max_ms * sr / 1000)
    c = np.concatenate([r[:m + 1], r[-m:]])
    lags = np.concatenate([np.arange(m + 1), np.arange(-m, 0)])
    i = int(np.argmax(np.abs(c)))
    return 1000.0 * float(lags[i]) / sr, float(np.abs(c[i]) / (np.median(np.abs(c)) + 1e-12))


def cab_drop(x, y, sr, nper=A2_NPERSEG, cmin=A2_COH_MIN, lo=A2_LO_HZ, hi=A2_HI_HZ):
    """A2's reading on one half: the median 20 log|H1| over the coherent 1-3 kHz bins less that over the coherent
    6-10 kHz bins. -> {"drop_db", "n_lo", "n_hi", "coh_hi_median"}."""
    import numpy as np
    import scipy.signal as ss

    f, sxx = ss.welch(x, sr, nperseg=nper)
    _, syy = ss.welch(y, sr, nperseg=nper)
    _, sxy = ss.csd(x, y, sr, nperseg=nper)
    coh = np.abs(sxy) ** 2 / (sxx * syy + 1e-40)
    hd = 20 * np.log10(np.abs(sxy) / (sxx + 1e-40) + 1e-30)
    bl = (f >= lo[0]) & (f < lo[1]) & (coh >= cmin)
    bh = (f >= hi[0]) & (f < hi[1]) & (coh >= cmin)
    drop = float(np.median(hd[bl]) - np.median(hd[bh])) if bl.any() and bh.any() else None
    allhi = (f >= hi[0]) & (f < hi[1])
    return {"drop_db": drop, "n_lo": int(bl.sum()), "n_hi": int(bh.sum()),
            "coh_hi_median": float(np.median(coh[allhi])) if allhi.any() else None}


def shift_later(y, n):
    """y advanced by n samples (n > 0: y lags x by n), zero-filled."""
    import numpy as np

    if n > 0:
        return np.concatenate([y[n:], np.zeros(n)])
    if n < 0:
        return np.concatenate([np.zeros(-n), y[:len(y) + n]])
    return np.asarray(y)


def cov_fit(x, y, a, b, n_taps, pre, ridge=A3_RIDGE):
    """Least-squares FIR (exact covariance method): y[n] ~ sum_k h[k] x[n + pre - k] for n in [a, b).
    Needs a >= n_taps - 1 - pre and b + pre <= len(x)."""
    import numpy as np
    from scipy.linalg import cho_factor, cho_solve

    A, B = a + pre, b + pre
    N = n_taps
    col = np.array([np.dot(x[A - d:B - d], x[A:B]) for d in range(N)])
    R = np.empty((N, N))
    for d in range(N):
        k = np.arange(N - d)
        i = np.arange(N - d - 1)
        corr = x[A - 1 - i - d] * x[A - 1 - i] - x[B - 1 - i - d] * x[B - 1 - i]
        v = col[d] + np.concatenate([[0.0], np.cumsum(corr)])
        R[k + d, k] = v
        R[k, k + d] = v
    r = np.array([np.dot(y[a:b], x[a + pre - k:b + pre - k]) for k in range(N)])
    R[np.diag_indices(N)] += ridge * np.trace(R) / N
    return cho_solve(cho_factor(R), r)


def apply_fir(h, x, c, d, pre):
    """The fitted filter on [c, d) (the taps read x[c - (N - 1 - pre) : d + pre])."""
    import numpy as np

    N = len(h)
    seg = x[c - (N - 1 - pre):d + pre]
    return np.convolve(seg, h, mode="valid")[:d - c]


def linear_residuals(x, y, sr, lag_ms, halves=HALVES, a3_sr=A3_SR, pre_ms=A3_PRE_MS, post_ms=A3_POST_MS,
                     ridge=A3_RIDGE, playing=None):
    """A3: the best linear filter fitted on one half, its residual on the other (dB of the other's power), both
    ways, after removing the A1 lag. With one half silent (`playing`: {half: bool}) the filter is fitted and read
    on the playing half alone (in-sample: a stricter test of a copy). -> {"A>B": dB, "B>A": dB} or {"A>A": dB}."""
    import numpy as np
    import scipy.signal as ss

    q = sr // a3_sr
    if q > 1:
        x = ss.decimate(x, q, ftype="fir", zero_phase=True)
        y = ss.decimate(y, q, ftype="fir", zero_phase=True)
    n = int(round((lag_ms or 0.0) * a3_sr / 1000))
    ya = shift_later(np.asarray(y, np.float64), n)
    x = np.asarray(x, np.float64)
    pre = int(pre_ms * a3_sr / 1000)
    N = pre + int(post_ms * a3_sr / 1000) + 1
    end = len(x) - abs(n) - pre - int(0.01 * a3_sr)
    seg = {h: (max(int(a * a3_sr), N), min(int(b * a3_sr), end)) for h, (a, b) in halves.items()}
    play = [h for h in halves if playing is None or playing.get(h)]
    pairs = (("A", "B"), ("B", "A")) if len(play) == 2 else ((play[0], play[0]),) if play else ()
    out = {}
    for fit, test in pairs:
        a, b = seg[fit]
        c, d = seg[test]
        if (b - a < a3_sr or d - c < a3_sr or np.sum(ya[c:d] ** 2) <= 0
                or np.sum(x[a:b] ** 2) <= 1e-12 * (b - a) or np.sum(x[c:d] ** 2) <= 1e-12 * (d - c)):
            out[f"{fit}>{test}"] = None                     # a silent DI half: no fit
            continue
        try:
            h = cov_fit(x, ya, a, b, N, pre, ridge)
        except np.linalg.LinAlgError:
            out[f"{fit}>{test}"] = None
            continue
        e = ya[c:d] - apply_fir(h, x, c, d, pre)
        out[f"{fit}>{test}"] = float(10 * np.log10(np.sum(e ** 2) / np.sum(ya[c:d] ** 2) + 1e-30))
    return out


def max_copy_corr(target, dis, sr, max_ms=A4_LAG_MS):
    """The largest peak |normalised cross-correlation| (+-max_ms) of the target with each DI. -> {name: r}."""
    import numpy as np

    out = {}
    m = int(max_ms * sr / 1000)
    t = np.asarray(target, np.float64)
    et = float(np.dot(t, t))
    for name, d in dis.items():
        d = np.asarray(d, np.float64)[:len(t)]
        ed = float(np.dot(d, d))
        if et <= 0 or ed <= 0:
            out[name] = None
            continue
        n = 1 << int(math.ceil(math.log2(len(t) + len(d))))
        c = np.fft.irfft(np.conj(np.fft.rfft(d, n)) * np.fft.rfft(t, n), n)
        v = np.concatenate([c[:m + 1], c[-m:]])
        out[name] = float(np.max(np.abs(v)) / math.sqrt(et * ed))
    return out


# crop_match2.py's measures (the data-quality audit), ported unchanged: 10-ms frames, 24 log bands 80 Hz-8 kHz.
CM_HOP = 480


def _cm_bands(x, nf=2048, sr=SR):
    import numpy as np

    fr = np.lib.stride_tricks.sliding_window_view(x, nf)[::CM_HOP] * np.hanning(nf)
    P = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    f = np.fft.rfftfreq(nf, 1 / sr)
    edges = np.geomspace(80, 8000, 25)
    return np.stack([P[:, (f >= edges[k]) & (f < edges[k + 1])].sum(1) for k in range(24)], 1)


def _cm_onset(Bp):
    import numpy as np

    E = 10 * np.log10(Bp + 1e-12)
    E = np.maximum(E, E.max() - 50)
    return np.maximum(np.diff(E, axis=0, prepend=E[:1]), 0).sum(1)


def _cm_best_corr(a, b, lag=10):
    import numpy as np

    best = -1.0
    for L in range(-lag, lag + 1):
        x, y = (a[L:], b[:len(b) - L]) if L >= 0 else (a[:len(a) + L], b[-L:])
        n = min(len(x), len(y))
        if n < 20 or x[:n].std() == 0 or y[:n].std() == 0:
            continue
        best = max(best, float(np.corrcoef(x[:n], y[:n])[0, 1]))
    return best


def _cm_chroma(x, nf=8192, hop=2400, sr=SR):
    import numpy as np

    fr = np.lib.stride_tricks.sliding_window_view(x, nf)[::hop] * np.hanning(nf)
    S = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    f = np.fft.rfftfreq(nf, 1 / sr)
    ok = (f > 70) & (f < 1500)
    pc = (np.round(12 * np.log2(f[ok] / 440)) % 12).astype(int)
    C = np.stack([S[:, ok][:, pc == k].sum(1) for k in range(12)], 1)
    return C / (C.sum(1, keepdims=True) + 1e-12), S[:, ok].sum(1)


def _cm_csim(a, b):
    import numpy as np

    (A, ea), (B, eb) = a, b
    m = min(len(A), len(B))
    A, B, ea, eb = A[:m], B[:m], ea[:m], eb[:m]
    ok = (ea > ea.max() * 1e-3) & (eb > eb.max() * 1e-3)
    if ok.sum() < 5:
        return None
    A = A[ok] - A[ok].mean(1, keepdims=True)
    B = B[ok] - B[ok].mean(1, keepdims=True)
    return float(np.mean((A * B).sum(1) / (np.linalg.norm(A, axis=1) * np.linalg.norm(B, axis=1) + 1e-12)))


def same_take(di, ref, sr=SR, halves=HALVES):
    """A5's measures per half, as `crop_match2.py`: {half: {"di_play_share", "chroma", "onset"}} (48 kHz crops)."""
    import numpy as np

    di = np.asarray(di, np.float32)
    ref = np.asarray(ref, np.float32)

    def fr(x):
        return 10 * np.log10(np.convolve(x.astype(np.float64) ** 2, np.ones(4800) / 4800, "valid")[::480] + 1e-20)

    gd = fr(di)
    thr_d = gd.max() - 40
    out = {}
    for h, (a, b) in halves.items():
        s = slice(int(a * sr), int(b * sr))
        out[h] = {"onset": round(_cm_best_corr(_cm_onset(_cm_bands(di[s])), _cm_onset(_cm_bands(ref[s]))), 3),
                  "chroma": _cm_csim(_cm_chroma(ref[s]), _cm_chroma(di[s])),
                  "di_play_share": round(float((gd[int(a * 100):int(b * 100)] > thr_d).mean()), 3)}
    return out


def di_processing(x, sr=SR, frame_s=D4_FRAME_S, play_db=D4_PLAY_DB):
    """D4's readings on a DI window: the median crest factor (dB) of its playing 100-ms frames, and the slope of
    their brightness (3-8 kHz over 0.1-1.5 kHz, dB) against their level (dB); kurtosis beside.
    -> {"crest_db", "bright_slope", "kurtosis", "frames"}."""
    import numpy as np

    x = np.asarray(x, np.float64)
    f = int(frame_s * sr)
    n = len(x) // f
    if n < 5:
        return {"crest_db": None, "bright_slope": None, "kurtosis": None, "frames": 0}
    fr = x[:n * f].reshape(n, f)
    rms = np.sqrt(np.mean(fr ** 2, 1)) + 1e-12
    ldb = 20 * np.log10(rms)
    play = ldb > ldb.max() - play_db
    if play.sum() < 5 or rms.max() <= 1e-9:
        return {"crest_db": None, "bright_slope": None, "kurtosis": None, "frames": int(play.sum())}
    crest = float(np.median(20 * np.log10(np.max(np.abs(fr[play]), 1) / rms[play])))
    W = np.abs(np.fft.rfft(fr * np.hanning(f), axis=1)) ** 2
    fq = np.fft.rfftfreq(f, 1 / sr)
    hf = 10 * np.log10(W[:, (fq >= 3000) & (fq < 8000)].sum(1) + 1e-30) - 10 * np.log10(
        W[:, (fq >= 100) & (fq < 1500)].sum(1) + 1e-30)
    slope = float(np.polyfit(ldb[play], hf[play], 1)[0])
    xs = fr[play].ravel()
    return {"crest_db": crest, "bright_slope": slope, "kurtosis": float(np.mean(xs ** 4) / np.mean(xs ** 2) ** 2),
            "frames": int(play.sum())}


def neg_eq(x, sr, p=NEG_EQ):
    """The constructed EQ'd DI: a cab-like band-pass with a mid peak, delayed (a linear copy that passes A1-A2)."""
    import numpy as np
    import scipy.signal as ss

    b, a = ss.butter(p["order"], list(p["band_hz"]), btype="band", fs=sr)
    y = ss.lfilter(b, a, x)
    bq, aq = ss.iirpeak(p["peak_hz"] / (sr / 2), p["peak_q"])
    y = y + p["peak_gain"] * ss.lfilter(bq, aq, y)
    d = int(round(p["delay_ms"] * sr / 1000))
    return p["gain"] * np.concatenate([np.zeros(d), y[:len(y) - d]])


def measure_pair(di, ref, sr=SR, halves=HALVES, playing=None):
    """A1-A3 of one DI/target pair (48 kHz, the crop's 10 s). `playing`: {half: bool}, the halves where the DI
    plays (A5's play share); a silent half is read but not used. -> the row's readings."""
    out = {"halves": {}, "playing": dict(playing) if playing else {h: True for h in halves}}
    for h, (a, b) in halves.items():
        s = slice(int(a * sr), int(b * sr))
        lag, prom = gcc_lag_ms(di[s], ref[s], sr)
        out["halves"][h] = {"lag_ms": round(lag, 3), "lag_prominence": round(prom, 1), "a2": cab_drop(di[s], ref[s], sr)}
    lags = [out["halves"][h]["lag_ms"] for h in halves if out["playing"].get(h)]
    lag_c, _ = gcc_lag_ms(di[int(halves["A"][0] * sr):], ref[int(halves["A"][0] * sr):], sr)
    out["lag_ms_crop"] = round(lag_c, 3)
    out["a3"] = linear_residuals(di, ref, sr, lags[0] if len(lags) == 1 else lag_c, playing=out["playing"])
    return out


def pair_status(m, max_corr=None, same_hash=False):
    """A1-A4 statuses of a `measure_pair` reading over its playing halves (A4 from the copy check, when given);
    with no playing half every measure fails (fail closed)."""
    hs = {h: v for h, v in m["halves"].items() if m.get("playing", {}).get(h, True)}
    a1 = combine_part([a1_status(v["lag_ms"], prominence=v.get("lag_prominence")) for v in hs.values()])
    a2 = a2_part([a2_half_status(v["a2"]["drop_db"], v["a2"]["n_lo"], v["a2"]["n_hi"]) for v in hs.values()])
    a3 = a3_status(list(m["a3"].values()))
    st = {"A1": a1, "A2": a2 if hs else "fail", "A3": a3}
    if max_corr is not None or same_hash:
        st["A4"] = a4_status(max_corr, same_hash)
    return st


# --- I/O ---------------------------------------------------------------------------------------------------------

def _save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=float))
    tmp.replace(path)


def _load(path):
    return json.loads(path.read_text()) if path.exists() else None


def out_root(args):
    return pathlib.Path(args.out).expanduser() if getattr(args, "out", None) else OUT


def ledger_ok():
    return f'"{LEDGER_ID}"' in (PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text()


def require_real(args):
    """Real runs write only to the default root and need the ledger entry; smoke runs need a scratch --out."""
    if getattr(args, "smoke", False):
        if not getattr(args, "out", None):
            raise SystemExit("--smoke writes into a scratch --out only")
        return
    if getattr(args, "out", None):
        raise SystemExit("--out is for smoke runs only")
    if not ledger_ok():
        raise SystemExit(f"the ledger has no {LEDGER_ID} entry (add it after the independent review)")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def mono(path, start_s=None, dur_s=None, sr=SR):
    """Mono float64 at `sr` (a window when start_s is given; zero-padded past the file's end)."""
    import numpy as np

    from learn import pretrain_set as PS

    x = PS.load_mono(path, sr, start_s, dur_s).astype(np.float64)
    if dur_s is not None:
        n = int(round(dur_s * sr))
        x = np.pad(x, (0, max(0, n - len(x))))[:n]
    return x


def label_table():
    return json.loads(LABEL_TABLE.read_text())["parts"]


def heldout_ok(slugs):
    """The data-review page's fail-closed held-out check (sets 1-3 catalogues only)."""
    from learn import build_data_review as BDR

    BDR.heldout_ok(sorted(slugs))


def crop_session(crop):
    """(record, session base dir, catalogue part, the session's DI file names, its mix tracks) of a crop."""
    rec = json.loads((pathlib.Path(crop) / "record.json").read_text())
    cpath = (rec.get("catalog") or {}).get("path", "")
    if "datasets-set3" in cpath:
        cat = json.loads(CAT3.read_text())
        s = next(s for s in cat["sessions"] if s["key"] == rec["session_key"])
    else:
        cat = json.loads(CAT12.read_text())
        ss_ = [s for s in cat["sessions"] if s["source"] == rec["source"] and s["song"] == rec["song"]]
        if len(ss_) != 1:
            raise SystemExit(f"{crop}: {len(ss_)} catalogue sessions")
        s = ss_[0]
    base = pathlib.Path(cat["root"]).expanduser() / s["path"]
    part = next(p for p in s["parts"] if p["part"] == rec["part"])
    files = sorted(s["files"]) if isinstance(s.get("files"), (list, dict)) else []
    dis = sorted({p["di"] for p in s["parts"] if p.get("di")} | {f for f in files if is_di_name(f)})
    return rec, base, part, dis, list(rec.get("included_mix_tracks") or [])


DI_NAME_RE = re.compile(r"(?<![A-Za-z])DI(?![A-Za-z])|DI$|DTDI|MicDI|TDP-|TDA-|DIRECT", re.I)


def is_di_name(name):
    """The bleed audit's DI naming (`bleed4.is_di`), less its "Pedal Board" (a processed track, not a DI)."""
    s = re.sub(r"-Norm.*$", "", pathlib.PurePosixPath(name).stem)
    s = re.sub(r"^\d+_", "", s)
    return bool(DI_NAME_RE.search(s)) and not re.search(r"bass", s, re.I)


# --- scope: every target and DI in use ---------------------------------------------------------------------------

def target_scope():
    """{slug: [uses]} over stage F, knob ceiling 2, the listening pages and the level prior's parts."""
    from learn import arm_a_mega53 as A
    from learn import build_data_review as BDR
    from learn import pretrain_set as PS

    used = BDR.amp_parts(A.pool_slugs())
    for f in sorted(PS.SECTIONS_MS.glob("*.json")):
        used.setdefault(f.stem, [])
        if "level prior" not in used[f.stem]:
            used[f.stem].append("level prior")
    for s in KNOWN_AMPS + KNOWN_FAILS:
        used.setdefault(s, [])
    return dict(sorted(used.items()))


def di_scope():
    """{di id: {"datasets", "band", "sections": [{id, start_s}]}} for part C's D build (pool and V_sep sections),
    plus every other inventory DI of those sessions (the self-built mixes' other guitars), read at the session's
    D-build section times. -> (scope, data_cleaning.Meta)."""
    from learn import data_cleaning as DC

    meta, secs = DC.Meta(), DC.build_sections()
    out = {}
    times = {}
    for sid, exs in sorted(secs.items()):
        sec = meta.sections[sid]
        parts = {e["part"] for e in exs}
        ds = "V_sep" if parts == {"vsep"} else "training pool"
        d = out.setdefault(sec["di"], {"datasets": [], "band": sec["band"], "sections": []})
        if ds not in d["datasets"]:
            d["datasets"].append(ds)
        d["sections"].append({"id": sid, "start_s": float(sec["start_s"])})
        times.setdefault(meta.inv[sec["di"]]["session_dir"], set()).add(float(sec["start_s"]))
    from learn import pretrain_set as PS

    own = {}
    for r in json.loads(PS.MANIFEST.read_text())["sections"]:
        if r.get("clean"):
            own.setdefault(r["di"], []).append(float(r["start_s"]))
    for di, rec in sorted(meta.inv.items()):
        sd = rec.get("session_dir")
        if di in out or sd not in times or rec.get("source") == "guitar-techs":
            continue
        mine = sorted(own.get(di, []))
        mine = [mine[int(round(k * (len(mine) - 1) / 3))] for k in range(4)] if len(mine) > 4 else mine
        ts = sorted(set(times[sd]) | set(mine))          # the session's mix times and where the DI itself plays
        out[di] = {"datasets": ["other guitar"], "band": rec.get("band"),
                   "sections": [{"id": f"{di}@{t:.1f}", "start_s": t} for t in ts]}
    return out, meta


# --- commands: calibration ---------------------------------------------------------------------------------------

def neg_dir(root):
    return root / "calibration" / "negatives"


def cmd_negatives(args):
    """The cab-off negatives (renders): each source crop's DI, levelled to -22.9 LUFS by one gain (no EQ, so the
    target is the amp alone), through PR12 at its clean and crunch starts with the cab section off; one process,
    isolate=True, a discarded priming render per DI; 6 renders. Never overwrites a stored negative."""
    import numpy as np

    from learn import direc_check as DC_
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS

    require_real(args)
    root = out_root(args)
    nd = neg_dir(root)
    man_p = nd / "negatives.json"
    man = _load(man_p) or {"plan": PLAN, "renders": {}, "primes": 0}
    todo = [(s, k) for s in NEG_SOURCES for k in ("cab_off_clean", "cab_off_crunch") if f"{s}|{k}" not in man["renders"]]
    if not todo:
        print("NEGATIVES DONE (stored)")
        return
    if PS.free_gb() < DISK_GUARD_GB:
        raise SystemExit(f"free disk below {DISK_GUARD_GB:.0f} GB")
    lt = label_table()
    LO._wait_cap()
    DS.wait_render_slot()
    rr = K.Renderer()
    n0 = 0
    try:
        if rr.r.isolate is not True:
            raise SystemExit("the renderer is not isolating renders")
        menu = rr.menu()
        last = None
        for slug, kind in todo:
            base = "clean" if kind == "cab_off_clean" else "crunch"
            sel, S = menu[NEG_AMP][K.START[base][NEG_AMP]]
            x = dict(S)
            x[("cabParameters", "sectionActive")] = "false"
            crop = pathlib.Path(lt[slug]["crop"])
            di = mono(crop / "di.wav")
            di = DC_.to_lufs(di, NEG_LEVEL_LUFS)
            lead = int(round(PS.TRIM_S * SR))
            di32 = np.concatenate([np.zeros(lead), di]).astype(np.float32)
            if last != slug:
                rr.render(di32, sel, x)                         # priming, discarded (a new DI)
                man["primes"] += 1
                n0 += 1
            last = slug
            y = np.asarray(rr.render(di32, sel, x), np.float64)
            n0 += 1
            y = (y.mean(axis=1) if y.ndim == 2 else y)[lead:lead + len(di)]
            peak = float(np.max(np.abs(y[int(0.25 * SR):]))) if len(y) else 0.0
            if not np.isfinite(y).all() or peak < 1e-3:
                raise SystemExit(f"{slug} {kind}: the cab-off render is silent or non-finite (peak {peak:.2e})")
            p = nd / f"{slug}__{kind}.flac"
            scale, sha = G.write_flac(p, y, SR)
            man["renders"][f"{slug}|{kind}"] = {"path": str(p), "scale": scale, "sha256": sha, "amp": NEG_AMP,
                                                "start": K.START[base][NEG_AMP], "cab": "off", "level_lufs": NEG_LEVEL_LUFS,
                                                "settings": LO.sdict(x), "peak": peak}
            _save(man_p, man)
            print(f"negative {slug} {kind}: peak {20 * math.log10(peak):.1f} dBFS", flush=True)
    finally:
        rr.close()
    man["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save(man_p, man)
    print(f"NEGATIVES DONE: {len(man['renders'])} renders stored, {n0} this process ({man['primes']} priming)")


def _copy_check(crop, ref, rec, base, part, dis):
    """A4 on a crop: (max |r| over the session's DIs at the crop window, a DI file with the target file's sha256,
    {DI: r}). The target file is the catalogue part's reference (the crop's main mic)."""
    t0 = float(rec.get("excerpt_start_s", 0.0))
    windows = {d: mono(base / d, t0, CROP_S) for d in dis if (base / d).exists()}
    corr = max_copy_corr(ref, windows, SR)
    known = rec.get("verified_source_sha256") or {}

    def h(name):
        short = pathlib.PurePosixPath(name).name
        v = known.get(name) or known.get(short)
        return v or (sha256_file(base / name) if (base / name).exists() else None)

    th = h(part["reference"])
    same = th is not None and any(h(d) == th for d in dis)
    vals = [v for v in corr.values() if v is not None]
    return (max(vals) if vals else None), same, corr


def cmd_calibrate(args):
    """Calibration (zero renders): the 18 known amps, the 2 known fails and the constructed negatives through
    A1-A4; CALIBRATION OK iff the known amps fail nothing, the known fails fail something and each declared
    negative fails its measure. Never overwrites an OK record."""
    import numpy as np

    from learn import direct_sound_gate as G

    require_real(args)
    root = out_root(args)
    path = root / "calibration" / "calibration.json"
    if (_load(path) or {}).get("verdict") == "OK" and not args.smoke:
        raise SystemExit(f"{path} reads OK: a rerun needs review; move it aside by hand first")
    lt = label_table()
    heldout_ok(KNOWN_AMPS + KNOWN_FAILS + NEG_SOURCES)
    bt = json.loads(BLEED_TABLE.read_text())
    man = _load(neg_dir(root) / "negatives.json") or {"renders": {}}
    rows = []

    def row(name, kind, di, ref, crop=None):
        m = measure_pair(di, ref)
        if crop is not None:
            rec, base, cpart, dis, _ = crop_session(crop)
            mc, same, corr = _copy_check(crop, ref, rec, base, cpart, dis)
        else:
            mc, same, corr = max_copy_corr(ref, {"own DI": di}, SR)["own DI"], False, None
        st = pair_status(m, mc, same)
        r = {"name": name, "kind": kind, "status": st, "readings": m, "a4_max_corr": mc, "a4_same_hash": same,
             "a4_corr": corr}
        rows.append(r)
        hs = m["halves"]
        print(f"{kind:15s} {name[:44]:44s} {st} lag {[hs[h]['lag_ms'] for h in 'AB']} "
              f"drop {[hs[h]['a2']['drop_db'] if hs[h]['a2']['drop_db'] is None else round(hs[h]['a2']['drop_db'], 1) for h in 'AB']} "
              f"bins {[hs[h]['a2']['n_hi'] for h in 'AB']} res {[None if v is None else round(v, 1) for v in m['a3'].values()]} "
              f"r {None if mc is None else round(mc, 3)}", flush=True)
        return r

    for slug in KNOWN_AMPS + KNOWN_FAILS:
        crop = pathlib.Path(lt[slug]["crop"])
        r = row(slug, "known" if slug in KNOWN_AMPS else "fail", mono(crop / "di.wav"), mono(crop / "reference.wav"), crop)
        r["stored_di_lag_ms"] = (bt.get(slug) or {}).get("di_lag_ms")
    missing = []
    for slug in NEG_SOURCES:
        crop = pathlib.Path(lt[slug]["crop"])
        di = mono(crop / "di.wav")
        row(f"{slug}|copy", "copy", di, di.copy())
        row(f"{slug}|eq", "eq", di, neg_eq(di, SR))
        for kind in ("cab_off_clean", "cab_off_crunch"):
            v = man["renders"].get(f"{slug}|{kind}")
            if v is None:
                missing.append(f"{slug}|{kind}")
                continue
            y = G.read_flac(pathlib.Path(v["path"]), v["scale"], v["sha256"])
            row(f"{slug}|{kind}", kind, di, np.asarray(y, np.float64))
    # D4 against the user's ear on the crops' DIs (sitting 1 of data-review-1, judged on the DI clip)
    d4 = None
    if args.ear_di:
        _, _, di_ear = ear_answers([], args.ear_di)
        heard = {slug: ear_di_verdict(h) for slug, h in di_ear.items() if slug in lt}
        meas, readings = {}, {}
        for slug in sorted(heard):
            f = di_processing(mono(pathlib.Path(lt[slug]["crop"]) / "di.wav")[int(HALVES["A"][0] * SR):])
            readings[slug] = {**f, "ear_clean": heard[slug]}
            meas[slug] = d4_status(f["crest_db"], f["bright_slope"])
        d4 = {"agreement": d4_agreement(heard, meas), "readings": readings,
              "thresholds": {"crest_db": D4_CREST_DB, "bright_slope": D4_SLOPE_MIN}}
        a = d4["agreement"]
        print(f"D4 against the ear: {a['agree']}/{a['heard']}; processed missed {a['processed_missed']}; "
              f"clean flagged {a['clean_flagged']}")
    verdict, probs = calibration_verdict(rows)
    if missing:
        probs.append(f"negatives not rendered: {missing} (run `negatives`)")
        verdict = "FAIL"

    def a2_val(r):
        ds = [r["readings"]["halves"][h]["a2"]["drop_db"] for h in "AB"
              if a2_half_status(**{k: r["readings"]["halves"][h]["a2"][k] for k in ("drop_db", "n_lo", "n_hi")}) != "ear"]
        return min(ds) if r["kind"] == "known" and ds else (max(ds) if ds else None)

    rec = {"plan": PLAN, "design": DESIGN, "smoke": bool(args.smoke), "verdict": verdict, "problems": probs,
           "thresholds": thresholds(), "threshold_moves": list(THRESHOLD_MOVES), "negatives": NEG_DECLARED,
           "must_fail": {k: list(v) for k, v in NEG_MUST_FAIL.items()},
           "margins": [margins(rows, "A2 drop (deciding halves)", a2_val,
                               lambda r: r["kind"] in ("fail", "copy", "cab_off_clean")),
                       margins(rows, "A3 residual (lowest direction)",
                               lambda r: min([v for v in r["readings"]["a3"].values() if v is not None], default=None),
                               lambda r: r["kind"] in ("copy", "eq")),
                       margins(rows, "A1 |lag| ms", lambda r: min(abs(r["readings"]["halves"][h]["lag_ms"]) for h in "AB"),
                               lambda r: r["kind"] in ("fail", "copy"))],
           "ear": [r["name"] for r in rows if r["kind"] == "known" and "ear" in r["status"].values()],
           "d4": d4, "rows": rows, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(path, rec)
    for p in probs:
        print("  problem:", p)
    print(f"known amps to the ear on A1 or A2 (not a fail): {rec['ear']}")
    print(f"CALIBRATION {verdict}")


def thresholds():
    return {"A1": {"band_hz": list(LAG_BAND_HZ), "min_ms": LAG_MIN_MS, "max_ms": LAG_MAX_MS, "search_ms": LAG_SEARCH_MS,
                   "prom_min": A1_PROM_MIN},
            "A2": {"nperseg": A2_NPERSEG, "coh_min": A2_COH_MIN, "lo_hz": list(A2_LO_HZ), "hi_hz": list(A2_HI_HZ),
                   "min_bins": A2_MIN_BINS, "drop_db": A2_DROP_DB},
            "A3": {"sr": A3_SR, "pre_ms": A3_PRE_MS, "post_ms": A3_POST_MS, "ridge": A3_RIDGE, "max_db": A3_MAX_DB},
            "A4": {"max_corr": A4_MAX_CORR, "lag_ms": A4_LAG_MS},
            "A5": {"play_min": A5_PLAY_MIN, "chroma_min": A5_CHROMA_MIN, "onset_min": A5_ONSET_MIN},
            "measure_play_min": MEASURE_PLAY_MIN,
            "A6": {"bleed_db": A6_BLEED_DB, "mix_take_db": A6_TAKE_DB},
            "stems": {"take_db": STEM_TAKE_DB, "strict_levels": list(STRICT_LEVELS)}}


def calibration_ok(root):
    rec = _load(root / "calibration" / "calibration.json") or {}
    return rec.get("verdict") == "OK" and rec.get("thresholds") == thresholds() and not rec.get("smoke"), rec


# --- commands: T0 targets ----------------------------------------------------------------------------------------

def same_part_in_mix(crop, rec, base, di, ref, own_extra=()):
    """A6's mix clause on a crop: every included mix track (less the own amp tracks) by the cleaning plan's
    same-part rule on each half (name partner, onsets, chroma), and the level of a confirmed one in dB of the
    target. -> {track: {half: {"same_part", "power_db", "chroma", "onset"}}}."""
    import numpy as np

    from learn import data_cleaning as DC

    t0 = float(rec.get("excerpt_start_s", 0.0))
    own = set(rec.get("removed_own_amp_tracks") or []) | set(own_extra or ())
    part = rec.get("part") or ""
    sr = DC.AN_SR
    import scipy.signal as ss

    def to24(x):
        return ss.resample_poly(x, 1, 2)

    di24, ref24 = to24(di), to24(ref)
    out = {}
    for t in rec.get("included_mix_tracks") or []:
        if t in own or DC.track_class(t) in ("drums",):
            continue
        p = base / t
        if not p.exists():
            continue
        y24 = to24(mono(p, t0, CROP_S))
        out[t] = {}
        for h, (a, b) in HALVES.items():
            s = slice(int(a * sr), int(b * sr))
            on = DC.best_corr(DC.onset_env(di24[s]), DC.onset_env(y24[s]))
            on_own = DC.best_corr(DC.onset_env(di24[s]), DC.onset_env(ref24[s]))
            ch = DC.chroma_sim(DC.chroma(ref24[s]), DC.chroma(y24[s]))
            e_t, e_r = float(np.sum(y24[s] ** 2)), float(np.sum(ref24[s] ** 2))
            sp = DC.same_part(ch, on, on_own, DC.name_partner(part, t))
            out[t][h] = {"same_part": sp, "counts": bool(sp and is_electric_take(t)),
                         "power_db": 10 * math.log10(e_t / e_r) if e_t > 0 and e_r > 0 else None,
                         "chroma": ch, "onset": on}
    return out


ACOUSTIC_RE = re.compile(r"acoustic|acc?gtr|\bac\b|nylon|piano|key|synth|bass|cello|string|vox|vocal", re.I)


def is_electric_take(name):
    """A track that can be another take of an electric guitar part: a guitar track by name, not an acoustic guitar
    or another instrument (those follow the riff without being a take of it: shown beside, never counted)."""
    from learn import data_cleaning as DC

    stem = pathlib.PurePosixPath(name).stem
    return DC.track_class(name) == "guitar" and not ACOUSTIC_RE.search(stem)


SESSION_WINDOWS = 3


def session_windows(slug, base, cpart, n=SESSION_WINDOWS):
    """A1-A3 on up to n of the level prior's passing sections of a part (evenly spaced), read from the session's DI
    and main mic, when the crop's DI is silent (the part feeds the prior through these sections, not its crop).
    -> {"starts", "status", "readings"} or None."""
    from learn import pretrain_set as PS

    f = PS.SECTIONS_MS / f"{slug}.json"
    if not f.exists():
        return None
    rows = [r for r in json.loads(f.read_text())["rows"] if r.get("passes") and r.get("snr_db") is not None]
    if not rows:
        return None
    rows.sort(key=lambda r: float(r["start_s"]))
    pick = [rows[int(round(k * (len(rows) - 1) / max(1, n - 1)))] for k in range(min(n, len(rows)))]
    starts = sorted({float(r["start_s"]) for r in pick})
    reads, a1, a2, a3 = [], [], [], []
    for t0 in starts:
        di, ref = mono(base / cpart["di"], t0, CROP_S), mono(base / cpart["reference"], t0, CROP_S)
        a5 = same_take(di, ref)
        m = measure_pair(di, ref, playing={h: (v["di_play_share"] or 0) >= MEASURE_PLAY_MIN for h, v in a5.items()})
        st = pair_status(m)
        reads.append({"start_s": t0, "status": st, "readings": m})
        a1.append(st["A1"])
        a2.append(st["A2"])
        a3.append(st["A3"])
    return {"starts": starts, "readings": reads,
            "status": {"A1": combine_part(a1), "A2": a2_part(a2), "A3": combine_part([x for x in a3])}}


def cmd_targets(args):
    """T0 on every amp-track target in use (zero renders): A1-A6, the stored di_lag_ms beside, per half."""
    root = out_root(args)
    require_real(args)
    ok, _ = calibration_ok(root)
    if not ok and not args.smoke:
        raise SystemExit("targets needs a real CALIBRATION OK under the current thresholds (run calibrate)")
    from learn import arm_a_mega53 as A

    lt = label_table()
    scope = target_scope()
    if args.limit:
        scope = dict(list(scope.items())[:args.limit])
    heldout_ok(scope)
    bt = json.loads(BLEED_TABLE.read_text())
    stage_f = set(A.pool_slugs())
    path = root / "t0" / "targets.json"
    done = (_load(path) or {}).get("parts", {})
    for k, (slug, uses) in enumerate(scope.items()):
        if slug in done:
            continue
        if slug not in lt:
            done[slug] = {"uses": uses, "error": "not a label-table part"}
            continue
        crop = pathlib.Path(lt[slug]["crop"])
        di, ref = mono(crop / "di.wav"), mono(crop / "reference.wav")
        rec, base, cpart, dis, _ = crop_session(crop)
        a5 = same_take(di, ref)
        m = measure_pair(di, ref, playing={h: (v["di_play_share"] or 0) >= MEASURE_PLAY_MIN for h, v in a5.items()})
        mc, same, corr = _copy_check(crop, ref, rec, base, cpart, dis)
        st = pair_status(m, mc, same)
        windows = None
        if not any(m["playing"].values()) and "level prior" in uses:
            windows = session_windows(slug, base, cpart)          # the crop is silent: read the prior's sections
            if windows:
                st.update(windows["status"])
        st["A5"] = combine_part([a5_half_status(v["di_play_share"], v["chroma"], v["onset"]) for v in a5.values()])
        bh = (bt.get(slug) or {}).get("halves") or {}
        st["A6"] = combine_part([a6_half_status(bh.get(h)) for h in HALVES])
        mix = None
        if slug in stage_f:
            own_x = [cpart["reference"], *(cpart.get("alternate") or []), *(cpart.get("simulated") or [])]
            mix = same_part_in_mix(crop, rec, base, di, ref, own_x)
            lv = [v["power_db"] for t in mix.values() for v in t.values() if v["counts"]]
            st["A6mix"] = a6_mix_status(lv)
        done[slug] = {"uses": uses, "band": lt[slug]["band"], "gain_class": lt[slug]["gain_class"], "status": st,
                      "readings": m, "a4_max_corr": mc, "a4_same_hash": same, "a4_corr": corr, "a5": a5,
                      "bleed_db": {h: (bh.get(h) or {}).get("bleed_db") for h in HALVES},
                      "stored_di_lag_ms": (bt.get(slug) or {}).get("di_lag_ms"), "mix_same_part": mix,
                      "session_windows": windows,
                      "in_mix": slug in stage_f}
        _save(path, {"plan": PLAN, "smoke": bool(args.smoke), "thresholds": thresholds(), "parts": done,
                     "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"{k + 1}/{len(scope)} {slug[:50]:50s} {st}", flush=True)
    print(f"TARGETS DONE: {len(done)} parts")


# --- commands: T0 DIs --------------------------------------------------------------------------------------------

def own_amp_tracks(rec, files):
    """The DI's own amp tracks (inventory `own`, the ones named with the part token first)."""
    own = list(rec.get("own") or [])
    part = rec.get("part") or ""
    named = [o for o in own if part and part.lower() in o.lower()]
    return [o for o in (named or own) if o in files]


class DiD2:
    """D2 on windows of one DI file (part A's measures and flags): the track-level hum lines once from the whole
    file (`clean_di.measure_di`), then per window the hum, hiss, clip runs and drop-outs, flagged by
    `clean_di.section_flags`."""

    def __init__(self, di_path, mains=None):
        import numpy as np

        from learn import clean_di as CD

        self.CD = CD
        self.x, self.sr = CD.load_native(di_path)
        self.mains = mains or CD.session_mains({m: [v] for m, v in CD.vote(di_path).items()})
        self.track, _ = CD.measure_di(self.x, self.sr, self.mains)
        self.y = CD.resample(self.x, self.sr, CD.SR)
        self.fdb = CD.frame_db(self.y)
        clips = CD.clip_runs(self.x)
        self.clip48 = (np.asarray(clips) * CD.SR / self.sr).astype(int)
        self.drops, self.cuts = CD.dropouts(self.x, self.sr, CD.play_level_db(self.fdb, CD.playing(self.fdb)))

    def window(self, start_s):
        """-> (flags, tags, row) of the 10-s window at start_s."""
        import numpy as np

        CD = self.CD
        s = int(round(start_s * CD.SR))
        L = int(CD.SEC_S * CD.SR)
        seg = self.y[s:s + L]
        r_ = CD.frames_in(s, s + L, len(self.fdb))
        sdb = self.fdb[r_.start:r_.stop]
        if not len(seg) or not len(sdb):
            return ["dropout"], ["window outside the file"], {}
        spl = CD.play_level_db(sdb, sdb >= self.fdb.max() - CD.PLAY_DB)
        f2, fs2 = CD.floor_spectrum(seg)
        ks = self.track.get("hum_harmonics") or []
        k = CD.SR / self.sr
        row = {"play_db": round(spl, 2),
               "hum_rel_db": round(CD.db(CD.line_power(f2, fs2, self.mains, ks)) - spl, 2) if ks and fs2 is not None else None,
               "hiss_rel_db": round(CD.db(CD.band_power_sum(f2, fs2, *CD.HISS_BAND)) - spl, 2) if fs2 is not None else None,
               "clip_runs": int(np.sum((self.clip48 >= s) & (self.clip48 < s + L))),
               "dropouts": int(sum(s <= int(d * k) < s + L for d, _ in self.drops)),
               "hard_cuts": int(sum(s <= int(v * k) < s + L for a, b in self.cuts for v in (a, b)))}
        flags, tags = CD.section_flags(row, self.track)
        return flags, tags, row


def window_d2(di_path, start_s, mains=None):
    return DiD2(di_path, mains).window(start_s)


def manifest_flags(man_rows, di, start_s):
    """Part A's stored flags and tags of a pool or V_sep section (None if part A has no row for it)."""
    for r in man_rows:
        if r["di"] == di and abs(float(r["start_s"]) - start_s) < 1e-6:
            return list(r.get("flags") or []), list(r.get("tags") or []), r.get("measures") or {}
    return None


def cmd_dis(args):
    """T0 on every DI in use (zero renders): D1 per section against the own amp track (A1, A2), D2 from part A's
    stored flags (pool and V_sep sections) or measured on the crop window (the crops' measure DIs), D3 by name."""
    import numpy as np

    from learn import data_cleaning as DC
    from learn import pretrain_set as PS

    require_real(args)
    root = out_root(args)
    k, n = args.shard
    scope, meta = di_scope()
    man_rows = json.loads(PS.MANIFEST.read_text())["sections"]
    lt = label_table()
    crops = {s: u for s, u in target_scope().items() if s in lt}
    jobs = [("di", d) for d in sorted(scope)] + [("crop", s) for s in sorted(crops)]
    jobs = [j for i, j in enumerate(jobs) if i % n == k][:args.limit or None]
    path = root / "t0" / f"dis-{k}of{n}.json"
    done = (_load(path) or {}).get("rows", {})
    for m, (kind, key) in enumerate(jobs):
        if f"{kind}:{key}" in done:
            continue
        if kind == "di":
            rec = meta.inv[key]
            sess = pathlib.Path(rec["session_dir"])
            files = sorted(f.name for f in sess.glob("*.wav"))
            amps = own_amp_tracks(rec, files)
            secs = []
            d2m = None
            for s in scope[key]["sections"]:
                di = mono(rec["path"], s["start_s"], CROP_S)
                d1 = None
                if amps:
                    cands = {a: mono(sess / a, s["start_s"], CROP_S) for a in amps}
                    amp_name = max(cands, key=lambda a: float(np.sum(cands[a] ** 2)))
                    amp = cands[amp_name]
                    hs = {}
                    for h, (a, b) in HALVES.items():
                        sl = slice(int(a * SR), int(b * SR))
                        lag, prom = gcc_lag_ms(di[sl], amp[sl], SR)
                        hs[h] = {"lag_ms": round(lag, 3), "lag_prominence": round(prom, 1),
                                 "a2": cab_drop(di[sl], amp[sl], SR)}
                    d1 = {"halves": hs, "amp_track": amp_name}
                mf = manifest_flags(man_rows, key, s["start_s"])
                src = "part A manifest"
                if mf is None:                                   # part A has no row here: measured on the window
                    d2m = d2m or DiD2(rec["path"])
                    mf = d2m.window(s["start_s"])
                    src = "measured here"
                d2 = {"flags": mf[0], "tags": mf[1], "status": d2_status(mf[0], key in PS.HUM_SUSPECT), "source": src}
                d4 = di_processing(di)
                d4["status"] = d4_status(d4["crest_db"], d4["bright_slope"])
                secs.append({"section": s["id"], "start_s": s["start_s"], "D1": d1, "D2": d2, "D4": d4})
            d1 = d1_status([h for x in secs if x["D1"] for h in x["D1"]["halves"].values()]) if amps else None
            d4_fail = [x["section"] for x in secs if x["D4"]["status"] == "fail"]
            st = {"D1": None if d1 is None else d1["status"],
                  "D2": combine_part([x["D2"]["status"] for x in secs]), "D3": d3_status(key),
                  "D4": "fail" if 2 * len(d4_fail) > len(secs) else "pass"}       # a majority of processed sections
            done[f"{kind}:{key}"] = {"di": key, "band": scope[key]["band"], "datasets": scope[key]["datasets"],
                                     "amp_tracks": amps, "status": st, "d1": d1, "d4_failing_sections": d4_fail,
                                     "sections": secs,
                                     "verdict": di_verdict(st)}
        else:
            crop = pathlib.Path(lt[key]["crop"])
            rec, base, cpart, dis, _ = crop_session(crop)
            di_path = base / cpart["di"]
            t0 = float(rec.get("excerpt_start_s", 0.0))
            flags, tags, row = window_d2(di_path, t0)
            src = next((r for r in meta.inv.values() if r.get("slug") == key), None)
            suspect = bool(src) and src["id"] in PS.HUM_SUSPECT
            d4 = di_processing(mono(crop / "di.wav")[int(HALVES["A"][0] * SR):])
            d4["status"] = d4_status(d4["crest_db"], d4["bright_slope"])
            st = {"D1": None, "D2": d2_status(flags, suspect), "D3": d3_status(cpart["di"]),   # D1: the target's A1-A2
                  "D4": d4["status"]}
            done[f"{kind}:{key}"] = {"slug": key, "uses": crops[key], "di_file": str(di_path), "window_s": t0,
                                     "status": st, "d2": {"flags": flags, "tags": tags, "row": row, "hum_suspect": suspect},
                                     "d4": d4, "inventory_di": src["id"] if src else None,
                                     "verdict": di_verdict({**st, "D1": "pass"})}
        _save(path, {"plan": PLAN, "smoke": bool(args.smoke), "shard": [k, n], "rows": done,
                     "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"{m + 1}/{len(jobs)} {kind} {key[-60:]}: {done[f'{kind}:{key}']['status']}", flush=True)
    print(f"DIS DONE {k}/{n}")


# --- commands: the stem scan -------------------------------------------------------------------------------------

def strict_session_vote(row, L, tol=STRICT_DETECT_TOL, margin=STRICT_BASE_MARGIN, need=0.8, base_need=0.9):
    """One session's vote at a stricter level L (the injection check's rule, moved to L): >= need of its targets
    (and of its room ones) read at least L - tol, and >= base_need of them read under L - margin uninjected."""
    tg = row.get("targets") or {}
    if not tg:
        return False
    ok = [r["inj"].get(L) is not None and r["inj"][L] >= L - tol for r in tg.values()]
    rooms = [o for o, r in zip(ok, tg.values()) if r.get("room")]
    base = sum(r["base"] is None or r["base"] < L - margin for r in tg.values()) / len(tg)
    return (sum(ok) / len(ok) >= need - 1e-9 and (not rooms or sum(rooms) / len(rooms) >= need - 1e-9)
            and base >= base_need - 1e-9)


def strict_floor(rows, levels=STRICT_LEVELS, default=STEM_TAKE_DB):
    """The strictest level every deciding session validates, else the plan's -30 dB."""
    from learn import data_cleaning as DC

    dec = [r for r in rows if r.get("deciding")]
    if {r["session"] for r in dec} != set(DC.INJECT_DECIDING):
        return default
    best = default
    for L in sorted(levels, reverse=True):
        if all(strict_session_vote(r, L) for r in dec):
            best = L
        else:
            break
    return best


def cmd_inject_strict(args):
    """The cleaning plan's injection check at -35 and -40 dB on its deciding sessions (zero renders); the stem scan
    adopts the strictest level that validates (`strict_floor`), else -30 dB. Never overwrites its record."""
    from learn import data_cleaning as DC

    require_real(args)
    root = out_root(args)
    path = root / "t0" / "injection-strict.json"
    if path.exists() and not args.smoke:
        raise SystemExit(f"{path} exists: a rerun needs review")
    meta, secs = DC.Meta(), DC.build_sections()
    sources = DC.injection_sources(DC.clean_injection_sessions(meta, secs))
    rows = []
    for name in DC.INJECT_DECIDING[:args.limit or None]:
        r = DC.inject_session(meta, sources[name], levels=STRICT_LEVELS)
        r["deciding"] = True
        rows.append(r)
        print(name, {L: strict_session_vote(r, L) for L in STRICT_LEVELS}, flush=True)
    floor = strict_floor(rows)
    _save(path, {"plan": PLAN, "smoke": bool(args.smoke), "levels": list(STRICT_LEVELS), "floor_db": floor,
                 "rows": [{**r, "targets": {t: {**x, "inj": {str(L): v for L, v in x["inj"].items()}}
                                            for t, x in r["targets"].items()}} for r in rows],
                 "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"STRICT FLOOR {floor:.0f} dB")


def stem_floor(root):
    rec = _load(root / "t0" / "injection-strict.json") or {}
    return float(rec["floor_db"]) if rec and not rec.get("smoke") else STEM_TAKE_DB


def scan_sessions(meta, scope):
    """{session dir: [DI ids in use]} over the D build's DIs (pool, V_sep)."""
    out = {}
    for di in scope:
        out.setdefault(meta.inv[di]["session_dir"], []).append(di)
    return dict(sorted(out.items()))


def guitar_sources(files):
    """Every guitar track of a session by name (amp tracks and DIs; bass excluded)."""
    from learn import data_cleaning as DC

    return [f for f in files if DC.track_class(f) == "guitar"]


PART_RE = re.compile(r"((?i:elec|ac(?:oustic)?)?\s*(?i:gtr)\s*_?\d+(?:[a-z](?![a-z]))?(?:\s*DT)?)")
GEAR_RE = re.compile(r"tdp-?\d*|tda-?\d*|\bm\d+\b|\btf\d+\b|\bdi\b|\bamp\b|\bmic\d*\b|\bclose\b|\bfar\b|norm.*$", re.I)


def guitar_part_key(name):
    """A guitar track's part, so a part's mics and DI group together: a numbered part (ElecGtr1, ElecGtr1c, ElecGtr2DT,
    GTR 1, AcousticGtr2; a lower-case letter suffix is a sub-part, upper-case DI/Mic/Amp are not), else the name less
    its gear and take tokens (Telefunken's "GTR DI", "GTR M80" and "GTR TF11" are one part)."""
    stem = re.sub(r"^\d+_", "", pathlib.PurePosixPath(name).stem)
    m = PART_RE.search(stem)
    if m:
        return re.sub(r"[\s_]", "", m.group(1)).lower()
    s = re.sub(r"[._-]\d+(?:[_-]\d+)*$", "", stem).replace("_", " ")
    s = GEAR_RE.sub(" ", s)
    return re.sub(r"[\s_.-]+", " ", s).strip().lower()


def scan_sources(files, energy):
    """The stem scan's sources: per guitar part, its loudest amp or mic track (a take reaches a room through the
    amp, and a part's mics are one take); its DI only when it has no amp track. energy: {track: mean square}."""
    groups = {}
    for f in guitar_sources(files):
        groups.setdefault(guitar_part_key(f), []).append(f)
    out = []
    for k in sorted(groups):
        amps = [f for f in groups[k] if not is_di_name(f)]
        pool = amps or groups[k]
        out.append(max(pool, key=lambda f: (energy.get(f, 0.0), f)))
    return out


def stem_pass(takes_db, floor):
    """A stem passes when every guitar source's take in it is under `floor` (None: none read)."""
    return all(v is None or v < floor for v in takes_db.values())


def cmd_stem_scan(args):
    """Every non-guitar track of every session in use: each guitar track's session-level take in it (the cleaning
    plan's estimator, `data_cleaning.TakeReader`, read against that guitar track itself). A stem passes when every
    guitar track reads under the floor (-30 dB, or `inject-strict`'s validated level)."""
    import gc

    from learn import data_cleaning as DC

    require_real(args)
    root = out_root(args)
    k, n = args.shard
    scope, meta = di_scope()
    sess = scan_sessions(meta, scope)
    jobs = [s for i, s in enumerate(sess) if i % n == k and (not args.only or args.only in s)][:args.limit or None]
    floor = stem_floor(root)
    path = root / "t0" / f"stems-{k}of{n}.json"
    done = (_load(path) or {}).get("sessions", {})
    idx, _ = DC.band_bins()
    for m, sd in enumerate(jobs):
        if sd in done:
            continue
        t = time.time()
        files = sorted(f.name for f in pathlib.Path(sd).glob("*.wav"))
        allg = guitar_sources(files)
        stems = [f for f in files if f not in allg]
        dur = max(DC.file_seconds(pathlib.Path(sd) / f) for f in files)
        Ys = {f: DC.stft(DC.load_window(pathlib.Path(sd) / f, 0.0, dur))[idx] for f in stems}
        gaud = {g: DC.load_window(pathlib.Path(sd) / g, 0.0, dur) for g in allg}
        gtr = scan_sources(allg, {g: float((a.astype("float64") ** 2).mean()) for g, a in gaud.items()})
        takes = {f: {} for f in stems}
        for g in gtr:
            S = DC.stft(gaud[g])[idx]
            if not (abs(S) > 0).any():
                continue
            got = DC.TakeReader(S, S).takes(Ys)
            for f, v in got.items():
                takes[f][g] = v
            del S
            gc.collect()
        del gaud
        done[sd] = {"dis": scope_dis(sess[sd]), "guitar_tracks": allg, "sources": gtr, "floor_db": floor,
                    "stems": {f: {"class": DC.track_class(f), "takes_db": takes[f], "pass": stem_pass(takes[f], floor)}
                              for f in stems}, "seconds": round(time.time() - t, 1)}
        del Ys
        gc.collect()
        _save(path, {"plan": PLAN, "smoke": bool(args.smoke), "shard": [k, n], "sessions": done,
                     "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        bad = [f for f, v in done[sd]["stems"].items() if not v["pass"]]
        print(f"{m + 1}/{len(jobs)} {pathlib.Path(sd).name}: {len(stems)} stems, {len(gtr)} guitar tracks, "
              f"failing {bad} ({time.time() - t:.0f} s)", flush=True)
    print(f"STEM SCAN DONE {k}/{n} (floor {floor:.0f} dB)")


def scope_dis(dis):
    return sorted(dis)


# --- commands: the lists -----------------------------------------------------------------------------------------

def ear_answers(paths, di_paths=()):
    """The user's ear, each answer id mapped through its page's items.json. -> (target clean {(slug, half): verdict},
    target amp {slug: verdict}, DI {slug: {half: verdict}}).
    - `paths`: exports that judged the targets (a data-review sitting heard on its main clip; the target-vs-DI page);
    - `di_paths`: data-review-1 exports whose amp items were judged on their DI clip (sitting 1, 2026-10-23: 'clean'
      is a clean, unprocessed DI; 'other' is a processed DI, an amp or a stem)."""
    clean, amp, di = {}, {}, {}
    pages = {"data-review-1": HOME / "listening/data-review-1/items.json",
             "target-vs-di-check": HOME / "listening/target-vs-di-check/items.json"}
    items = {}
    for page, p in pages.items():
        if p.exists():
            for it in json.loads(p.read_text())["items"]:
                items[it["id"]] = it
    for p, about_di in [(q, False) for q in paths or ()] + [(q, True) for q in di_paths or ()]:
        d = json.loads(pathlib.Path(p).expanduser().read_text())
        for a in d.get("answers") or []:
            it = items.get(a["id"])
            if it is None or not a.get("verdict"):
                continue
            if d.get("page") == "data-review-1" and it.get("section") == "amp":
                if about_di:
                    di.setdefault(it["slug"], {})[it["half"]] = a["verdict"]
                else:
                    clean[(it["slug"], it["half"])] = a["verdict"]
            elif d.get("page") == "target-vs-di-check" and not about_di:
                slug = (it.get("private") or {}).get("slug")
                if slug:
                    amp[slug] = a["verdict"]
    return clean, amp, di


def d4_agreement(ear, measured):
    """How the measured D4 agrees with the ear on the heard DIs. ear: {slug: True clean / False processed};
    measured: {slug: 'pass' | 'fail'}. -> counts and the disagreements."""
    both = [k for k in ear if ear[k] is not None and k in measured]
    tp = [k for k in both if ear[k] is False and measured[k] == "fail"]
    fn = [k for k in both if ear[k] is False and measured[k] == "pass"]
    tn = [k for k in both if ear[k] is True and measured[k] == "pass"]
    fp = [k for k in both if ear[k] is True and measured[k] == "fail"]
    return {"heard": len(both), "agree": len(tp) + len(tn), "processed_caught": len(tp), "processed_missed": sorted(fn),
            "clean_passed": len(tn), "clean_flagged": sorted(fp)}


def ear_clean_of(slug, clean, halves_used=("A", "B")):
    """True if every half used was heard 'clean', False if any half was heard otherwise, None if not all heard."""
    vs = [clean.get((slug, h)) for h in halves_used]
    if any(v is not None and v != "clean" for v in vs):
        return False
    return True if all(v == "clean" for v in vs) else None


def ear_amp_of(slug, amp):
    v = amp.get(slug)
    return None if v in (None, "unsure") else v == "amp"


def rederive_prior(sections_dir, passing, crop_only_a5):
    """The level prior on passing parts: {band: [snr_db]} from multi-section rows (`passes`, finite snr) of the
    parts in `passing`; a part failing A5 on its crop alone keeps its other sections (`crop_only_a5`: {slug:
    crop_start_s}). -> (prior, per-part counts)."""
    vals, counts = {}, {}
    for f in sorted(pathlib.Path(sections_dir).glob("*.json")):
        d = json.loads(f.read_text())
        slug = d.get("slug") or f.stem
        if slug not in passing and slug not in crop_only_a5:
            continue
        c0 = crop_only_a5.get(slug)
        kept = 0
        for r in d["rows"]:
            if not r.get("passes") or r.get("snr_db") is None:
                continue
            if c0 is not None and abs(float(r["start_s"]) - float(c0)) < CROP_S:
                continue
            vals.setdefault(d.get("band") or f.stem, []).append(float(r["snr_db"]))
            kept += 1
        counts[slug] = kept
    return vals, counts


def prior_summary(vals):
    import numpy as np

    allv = [v for vs in vals.values() for v in vs]
    if not allv:
        return {"n": 0}
    return {"n": len(allv), "bands": len(vals), "median": float(np.median(allv)),
            "p5": float(np.percentile(allv, 5)), "p95": float(np.percentile(allv, 95))}


def merged_shards(root, prefix, key):
    out = {}
    for p in sorted((root / "t0").glob(f"{prefix}-*of*.json")):
        out.update((_load(p) or {}).get(key, {}))
    return out


def cmd_lists(args):
    """The trusted lists (zero renders): targets by use, DIs, stems, the ear's queue, the re-derived level prior."""
    from learn import pretrain_set as PS

    require_real(args)
    root = out_root(args)
    tg = (_load(root / "t0" / "targets.json") or {}).get("parts")
    if not tg:
        raise SystemExit("run `targets` first")
    dis = merged_shards(root, "dis", "rows")
    stems = merged_shards(root, "stems", "sessions")
    clean, amp, di_ear = ear_answers(args.ear or [], args.ear_di or [])
    di_rows = {k: v for k, v in dis.items() if k.startswith("di:")}
    crop_rows = {k[5:]: v for k, v in dis.items() if k.startswith("crop:")}
    # the ear on the crops' DIs is authoritative (user, 2026-10-23): heard processed -> excluded; heard clean -> D4 passes
    ear_of_slug = {slug: ear_di_verdict(h) for slug, h in di_ear.items()}
    ear_of_di = {}
    for slug, cr in crop_rows.items():
        e = ear_of_slug.get(slug)
        if e is not None and cr.get("inventory_di"):
            prev = ear_of_di.get(cr["inventory_di"])
            ear_of_di[cr["inventory_di"]] = e if prev is None else (prev and e)
    agreement = d4_agreement({s: e for s, e in ear_of_slug.items() if s in crop_rows},
                             {s: crop_rows[s]["status"].get("D4") for s in crop_rows})

    def with_ear(st, e):
        st = dict(st)
        if e is True:
            st["D4"] = "pass"
        elif e is False:
            st["D4"] = "fail"
            st["ear"] = "heard processed"
        return st

    for slug, cr in crop_rows.items():
        cr["status"] = with_ear(cr["status"], ear_of_slug.get(slug))
        cr["verdict"] = di_verdict({**cr["status"], "D1": "pass"})
        cr["ear"] = ear_of_slug.get(slug)
    for k, v in di_rows.items():
        e = ear_of_di.get(k[3:])
        v["status"] = with_ear(v["status"], e)
        v["verdict"] = di_verdict(v["status"])
        v["ear"] = e
        v["excluded_sections"] = [] if e is True else list(v.get("d4_failing_sections") or [])
    targets = {}
    for slug, r in tg.items():
        if "status" not in r:
            targets[slug] = {"verdict": "excluded", "why": [r.get("error", "not measured")], "uses": r.get("uses")}
            continue
        v, why = target_verdict(r["status"], ear_clean_of(slug, clean), ear_amp_of(slug, amp),
                                disputed=slug in EAR_DISPUTED, in_mix=r.get("in_mix", False))
        targets[slug] = {"verdict": v, "why": why, "uses": r["uses"], "band": r["band"], "status": r["status"],
                         "bleed_db": r["bleed_db"], "lag_ms": {h: r["readings"]["halves"][h]["lag_ms"] for h in HALVES},
                         "a3": r["readings"]["a3"], "a5": r["a5"]}
    for slug, cr in crop_rows.items():                              # a target's measure DI must pass D2-D4 too
        if slug in targets and cr["verdict"][0] == "excluded" and targets[slug]["verdict"] != "excluded":
            targets[slug]["verdict"] = "excluded"
            targets[slug]["why"] = [f"measure DI: {', '.join(cr['verdict'][1])}"]
    pool_d4 = {}
    for k, v in di_rows.items():
        for x in v["sections"]:
            if "training pool" in v["datasets"] or "V_sep" in v["datasets"]:
                b = pool_d4.setdefault(v["band"], {"sections": 0, "excluded": 0})
                b["sections"] += 1
                b["excluded"] += bool(v["verdict"][0] == "excluded" or x["section"] in v["excluded_sections"])
    passing = {s for s, r in tg.items() if "status" in r and all(r["status"].get(m) == "pass" or r["status"].get(m) == "ear"
                                                                  for m in ("A1", "A2", "A3", "A4", "A6"))}
    crop_only = {s: json.loads((pathlib.Path(label_table()[s]["crop"]) / "record.json").read_text())["excerpt_start_s"]
                 for s in passing if tg[s]["status"].get("A5") == "fail"}
    prior, counts = rederive_prior(PS.SECTIONS_MS, passing - set(crop_only), crop_only)
    old = PS.ratio_values()
    trusted_stems = {sd: sorted(f for f, v in r["stems"].items() if v["pass"]) for sd, r in stems.items()}

    def uses(v, u):
        return [s for s, r in targets.items() if r["verdict"] == v and u in (r.get("uses") or [])]

    rec = {"plan": PLAN, "smoke": bool(args.smoke), "ear_files": [str(p) for p in args.ear or []],
           "ear_di_files": [str(p) for p in args.ear_di or []],
           "targets": targets, "dis": {k[3:]: {"verdict": v["verdict"], "status": v["status"], "datasets": v["datasets"],
                                               "band": v["band"], "ear": v["ear"],
                                               "excluded_sections": v["excluded_sections"]} for k, v in di_rows.items()},
           "measure_dis": {s: {"verdict": v["verdict"], "status": v["status"], "d2": v["d2"], "d4": v.get("d4"),
                               "ear": v.get("ear")} for s, v in crop_rows.items()},
           "d4_agreement_with_ear": agreement, "d4_pool_sections_by_band": pool_d4,
           "excluded_sections": sorted(x for v in di_rows.values() if v["verdict"][0] == "trusted"
                                       for x in v["excluded_sections"]),
           "stems": trusted_stems, "stem_floor_db": stem_floor(root),
           "v_real": uses("trusted", "stage F"), "v_real_pending": uses("pending ear", "stage F"),
           "kc2_trusted": uses("trusted", "knob ceiling 2"), "kc2_pending": uses("pending ear", "knob ceiling 2"),
           "k_dis": sorted(d[3:] for d, v in di_rows.items() if v["verdict"][0] == "trusted" and "V_sep" in v["datasets"]
                           and v["band"] not in K_OUT_BANDS),
           "training_dis": sorted(d[3:] for d, v in di_rows.items() if v["verdict"][0] == "trusted"
                                  and "training pool" in v["datasets"]),
           "level_prior": {"rederived": prior, "rederived_summary": prior_summary(prior), "old_summary": prior_summary(old),
                           "per_part": counts, "crop_only_a5": crop_only},
           "ear_queue": sorted([s for s, r in targets.items() if r["verdict"] == "pending ear"]),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(root / "t0" / "trusted.json", rec)
    for v in ("trusted", "pending ear", "excluded"):
        print(f"targets {v}: {sum(1 for r in targets.values() if r['verdict'] == v)}")
    print(f"V-real: {len(rec['v_real'])} trusted, {len(rec['v_real_pending'])} pending the ear; knob ceiling 2: "
          f"{len(rec['kc2_trusted'])} trusted, {len(rec['kc2_pending'])} pending")
    print(f"DIs: {sum(1 for v in di_rows.values() if v['verdict'][0] == 'trusted')} trusted of {len(di_rows)}; "
          f"K's DIs {len(rec['k_dis'])} ({REMOVED})")
    print(f"stems passing: {sum(len(v) for v in trusted_stems.values())} in {len(trusted_stems)} sessions "
          f"(floor {rec['stem_floor_db']:.0f} dB)")
    print(f"level prior: re-derived {rec['level_prior']['rederived_summary']}; old {rec['level_prior']['old_summary']}")
    a = agreement
    print(f"D4 against the ear: {a['agree']}/{a['heard']} agree; processed caught {a['processed_caught']}, missed "
          f"{a['processed_missed']}; clean passed {a['clean_passed']}, flagged {a['clean_flagged']}")
    print("pool and V_sep sections excluded by DI checks (D1-D4, the ear), per band: "
          + ", ".join(f"{b} {v['excluded']}/{v['sections']}" for b, v in sorted(pool_d4.items())))


# --- commands: the re-reads (zero renders) -----------------------------------------------------------------------

def subset_stats(rows, keep):
    """CR.stats over [(band, value)] of the rows whose slug is kept. rows: [(slug, band, value)]."""
    from learn import confirm_run as CR

    sel = [(b, v) for s, b, v in rows if s in keep]
    if len({b for b, _ in sel}) < 2:
        return {"n": len(sel), "note": "too few bands"}
    return CR.stats(sel)


def cmd_reread(args):
    """The plan's re-reads on the trusted panel (zero renders), each beside its stored headline: knob ceiling's
    K_S - S, K_S ceiling's extension, knob ceiling 2's (e) and time effects, amp choice; and the listening
    footnotes. Prints the dated notes for the results docs."""
    import math as _m

    from learn import every_control as EC
    from learn import knob_ceiling as K
    from learn import knob_ceiling2 as K2
    from learn import ks_extend as KS

    require_real(args)
    root = out_root(args)
    tr = _load(root / "t0" / "trusted.json")
    if not tr:
        raise SystemExit("run `lists` first")
    keep = set(tr["kc2_trusted"])                       # the panel: no measured fail (the plan's "12 parts") ...
    if not args.trusted_only:
        keep |= set(tr["kc2_pending"])                  # ... the ear's confirmation pending beside
    cells = [json.loads(p.read_text()) for p in sorted((K.OUT / "cells").glob("*/*/result.json"))]
    out = {"panel": sorted(keep), "trusted_only": bool(args.trusted_only)}
    ks_vs_s = [(c["slug"], c["band"], K.cell_rows(c)[0]["KS_vs_S"]) for c in cells if "KS_vs_S" in K.cell_rows(c)[0]]
    out["knob ceiling K_S - S (cells)"] = {"all": subset_stats(ks_vs_s, {s for s, _, _ in ks_vs_s}),
                                          "trusted": subset_stats(ks_vs_s, keep)}
    base, res = KS.base_figures(), KS.stored_results()
    sub = lambda d: {k: v for k, v in d.items() if k[0] in keep}                 # noqa: E731
    out["K_S ceiling (extension, at stop)"] = {"all": KS.summarise(base, res)["estimate_at_stop"]["all"],
                                               "trusted": KS.summarise(sub(base), sub(res))["estimate_at_stop"]["all"]}
    s1 = [json.loads(p.read_text()) for p in sorted((K2.OUT / "stage1").glob("*/[AB].json"))]
    e = [(r["slug"], r["band"], r["gain_class"], _m.log(r["held"] / r["start_held"])) for r in s1]
    out["knob ceiling 2 (e)"] = {"all": K2._stats(K2._per_part([x for x in e])),
                                 "trusted": K2._stats(K2._per_part([x for x in e if x[0] in keep]))}
    s2 = [(p.parent.name, json.loads(p.read_text())) for p in sorted((K2.OUT / "stage2").glob("*/[AB].json"))]
    t = [(r.get("slug") or slug, r["band"], r["gain_class"], _m.log(r["held"] / r["start_held"])) for slug, r in s2]
    out["knob ceiling 2 time effects (stage 2 - stage 1, judge)"] = {
        "all": K2._stats(K2._per_part(t)), "trusted": K2._stats(K2._per_part([x for x in t if x[0] in keep])),
        "large_cells_on_failing_parts": sorted([(x[0], round(x[3], 3)) for x in t if x[0] not in keep and x[3] < -0.05])}
    ac = EC.amp_choice_rows(cells)
    out["amp choice (part-weighted mean; band-weighted beside)"] = {
        "all": subset_stats([(s, b, v) for s, b, _, v in ac], {s for s, *_ in ac}),
        "trusted": subset_stats([(s, b, v) for s, b, _, v in ac], keep)}
    tv = tr["targets"]
    out["listening footnotes"] = {
        "record-match trial 5 (Today's The Day ElecGtr07)": tv.get("cambridge-Today's_The_Day-ElecGtr07", {}).get("verdict"),
        "arm A trials 1-3, 8": {s: tv.get(s, {}).get("verdict") for s in (
            "telefunken-First_Offering-GTR_1", "telefunken-Long_Way_Home-GTR", "telefunken-Bloomlight-GTR",
            "cambridge-Prodigal-ElecGtr5")},
        "arm A trials 4-7 ('4 of 4 heard arm A')": {s: tv.get(s, {}).get("verdict") for s in (
            "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr2", "cambridge-femme-elecgtr3",
            "cambridge-Today's_The_Day-ElecGtr10", "cambridge-Drag_Me_Down-ElecGtr4")},
        "knob ceiling 2 clear-gain effect trials (2, 4, 7)": {s: tv.get(s, {}).get("verdict") for s in (
            "telefunken-Sculptor's_Request-GTR_2", "telefunken-Blind_Spots-GTR", "cambridge-Prodigal-ElecGtr5")}}
    out["level prior"] = {k: tr["level_prior"][k] for k in ("rederived_summary", "old_summary")}
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save(root / "t0" / "reread.json", out)
    date = time.strftime("%Y-%m-%d")

    def f(s):
        m = s.get("mean") if isinstance(s, dict) else None
        if m is None:
            return json.dumps(s)[:120]
        return f"{m:+.3f} [{s.get('lo90', float('nan')):+.3f}, {s.get('hi90', float('nan')):+.3f}]"

    print(f"Dated notes ({date}; trusted panel of {len(keep)} parts):")
    for k_, v in out.items():
        if isinstance(v, dict) and "trusted" in v:
            print(f"- {k_}: all {f(v['all'])}; trusted {f(v['trusted'])}")
    print("- listening:", json.dumps(out["listening footnotes"]))
    print("- level prior:", json.dumps(out["level prior"]))


# --- main --------------------------------------------------------------------------------------------------------

def parse_shard(s):
    k, n = (int(v) for v in s.split("/"))
    if not 0 <= k < n:
        raise argparse.ArgumentTypeError(s)
    return k, n


def main(argv=None):
    ap = argparse.ArgumentParser(prog="verify_tracks", description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("negatives", "calibrate", "targets", "dis", "inject-strict", "stem-scan", "lists",
                                    "reread"))
    ap.add_argument("--shard", type=parse_shard, default=(0, 1))
    ap.add_argument("--out", default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default=None, help="smoke runs: only sessions whose path contains this")
    ap.add_argument("--ear", action="append", help="an exported answers file judging the targets")
    ap.add_argument("--ear-di", action="append", help="a data-review-1 export judged on the DI clip (sitting 1)")
    ap.add_argument("--trusted-only", action="store_true", help="reread: only parts the ear has confirmed")
    args = ap.parse_args(argv)
    if (args.limit or args.only) and not args.smoke:
        raise SystemExit("--limit and --only are for smoke runs (with --smoke and --out)")
    {"negatives": cmd_negatives, "calibrate": cmd_calibrate, "targets": cmd_targets, "dis": cmd_dis,
     "inject-strict": cmd_inject_strict, "stem-scan": cmd_stem_scan, "lists": cmd_lists, "reread": cmd_reread}[args.cmd](args)


if __name__ == "__main__":
    main()
