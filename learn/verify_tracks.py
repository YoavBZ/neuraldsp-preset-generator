"""The trusted-data plan's verification standard and stage T0 (`docs/trusted-data-strategy-plan.md`, approved
2026-10-23 with its recorded decisions; the thresholds and their calibration are in
`docs/trusted-data-t0-design.md`). Development data only: sets 1-3's label-table parts, part C's pool and
V_sep; nothing from sets 4-6, Guitar-TECHS P3 or a reservation in `dev-test-ledger.json` is opened.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    $MAIN -u -m learn.verify_tracks negatives       # calibration's Morgan cab-off renders: 8, plus 6 priming (one process, isolate)
    $MAIN -m learn.verify_tracks calibrate          # CALIBRATION OK | FAIL (zero renders; reads the negatives' renders)
    $MAIN -m learn.verify_tracks targets            # A1-A6 on every amp-track target in use (needs CALIBRATION OK)
    $MAIN -m learn.verify_tracks dis --shard k/3    # D1-D3 on every DI in use (pool, V_sep, the crops' measure DIs)
    $MAIN -m learn.verify_tracks inject-strict      # the take estimator at -35 and -40 dB (a stricter stem floor?)
    $MAIN -m learn.verify_tracks stem-scan --shard k/3   # every guitar track's take in every non-guitar stem
    $MAIN -m learn.verify_tracks lists --ear-di SITTING1.json [--ear EXPORT.json ...]   # the lists, the ear's queue,
                                                    # the level prior; pass every export each time (a run that would
                                                    # drop an earlier run's export refuses)
    $MAIN -m learn.verify_tracks reread             # zero-render re-reads of the results that rest on failing parts

**The standard** (plan (a)), per judge half of a crop (A 1.0-5.5 s, B 5.5-10.0 s), the crop's `reference.wav`
against its `di.wav`:
- **A1, mic delay:** GCC-PHAT lag, DI to target, over 80 Hz-4 kHz (the full band reads 0 ms on several amps, whose
  tracks carry a zero-lag path above 4 kHz; the bleed audit's stored `di_lag_ms`, read at 24 kHz over +-40 s, agrees
  with the band-limited reading and is shown beside). Pass 0.1 <= |lag| <= 30 ms; a negative lag, or a GCC peak under
  12x the median (unreadable), goes to the ear.
- **A2, cab roll-off:** H1 = S_xy/S_xx (Welch, 4096, Hann), bins with coherence >= 0.5: the median |H| over 6-10 kHz
  under the median over 1-3 kHz by at least 12 dB (the plan's), over at least `A2_MIN_BINS` coherent bins in each
  band, passes; under 3.3 dB over the same gate fails (ruling (a)); between, or under the gate, the ear. A part fails if
  a half fails, passes if a half passes and none fails, else goes to the ear.
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
- **DIs:** D1, A1 and A2 against the DI's own amp track over its sections (medians); D2, no clipping or drop-outs on
  the window and no hum (part A's flags and hum-suspect list; decision 2 excludes hummy measure DIs), hiss and bleed
  shown; D3, not a line out or processor output by name; D4 (user, 2026-10-23), the DI is unprocessed: crest factor
  and brightness against level, calibrated on the user's sitting-1 DI verdicts.

**The rule:** a measured fail of A1-A6 or D1-D3 is excluded (decision 2). The ear decides the rest: a DI heard
processed is excluded; heard clean clears the heard window only, and a heard-clean DI that D4 flags is a conflict for
the user; D4 alone never decides an unheard DI (a flag, D1 to the ear and DI-only parts wait for the ear, as does a
seeded sample of D4-passed DIs). A target is trusted only when it passes the measures and the user has heard it clean
and, where A1 or A2 went to the ear, as an amp. Quicksand ElecGtr2 and Today's The Day ElecGtr07 stay excluded: their
measured fails stand (the user, 2026-10-24). Every DI is heard before it counts (the user, 2026-10-24), and a session's
stems count once its stem spot-check is heard clean. `lists` writes the ear queue (every item the ear must hear) and
recomputes every verdict from the stored readings under the current thresholds. Thresholds move only to separate the
calibration's known cases (`THRESHOLD_MOVES`; revised after the review of #281).

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
A2_MIN_BINS = 17                      # a pass needs this many coherent bins in each band (5% of 6-10 kHz's 342)
A2_PASS_DB = 12.0                     # the plan's: a drop of at least this (over enough bins) passes
A2_FAIL_DB = 3.3                      # a drop under this fails (over the same 17-bin gate); between: the ear
# A2's coherence-free cab check (calibration fix, 2026-10-23): the target's spectral slope over 5-10 kHz less its DI's
# (dB per octave). A speaker cab falls steeply above about 5 kHz; an amp without one keeps the DI's top or adds to it.
# Where the coherent drop goes to the ear, a relative slope above the fail line fails A2. The line is A2's own fail line
# (3.3 dB) spread over the two octaves between its bands (1-3 and 6-10 kHz), so nothing new is fitted. It reads only on
# halves whose bleed is under -30 dB (bleed rules a cab-filtered target's top end).
A2_SLOPE_BAND_HZ = (5000.0, 10000.0)
A2_SLOPE_FAIL = -A2_FAIL_DB / 2.0      # dB/oct

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
D4_SAMPLE_SEED = 20261103             # the D4-passed DIs sampled for the ear (one per band; set here); also the
                                      # window of an unheard DI queued under the every-DI rule (user, 2026-10-24)
STEM_CHECK_FILE = "stem-checks.json"  # the stem spot-check's choice per session (stored: the queue stays stable)
STEM_CHECK_MIN_SHARE = 0.10           # the checked stem must play on this share of the window (its own file's level)
STEM_CHECK_TRIES = 5                  # stems tried per session, nearest the floor first
D4_GRID = {"crest": (6.5, 10.5, 0.1), "slope": (-0.4, 0.8, 0.02)}   # D4's rule search (in-sample and leave-one-out)

# --- D3: by name -----------------------------------------------------------------------------------------------
D3_RE = re.compile(r"pedal\s*board|line\s*out|lineout|\bfx\b|\bsim\b|kemper|\baxe\b|helix|\bpod\b|processed|"
                   r"re-?amp|effects?\b|\bwet\b", re.I)

# The plan's thresholds that calibration moved or added, toward keeping the known amps (plan (a): "each move is
# recorded"); revised after the code review of #281.
THRESHOLD_MOVES = (
    {"threshold": "A2", "plan": "pass >= 12 dB", "now": f"over >= {A2_MIN_BINS} coherent bins in both bands: pass >= "
                                                         f"{A2_PASS_DB} dB, fail < {A2_FAIL_DB} dB, between to the ear; "
                                                         f"fewer bins: the ear",
     "why": "the plan's pass is kept. Known amps read 6.2 dB (colour-me-red 03, half A) and 10.3 dB (Signs 2, half A): "
            "they go to the ear, not to a pass (the review: the parts behind a lower pass all have D4-flagged DIs). The "
            "fail line sits midway between Prodigal ElecGtr5's 0.4 dB and colour-me-red 03's 6.2 dB; unchanged when the "
            "re-review cut the known amps to 11"},
    {"threshold": "A2_MIN_BINS", "plan": None, "now": A2_MIN_BINS,
     "why": "the plan sends 'too few coherent bins above 6 kHz' to the ear without a number: 17 bins (5% of the band). "
            "The re-review's ruling (a): a fail must pass the same gate as a pass, so no new number is fitted; a half "
            "under it goes to the ear and stays out until heard (Adam Buckley ElecGtr5's DI, one bin at -19 dB, and "
            "Quicksand ElecGtr2, 12 and 10 bins, go to the ear)"},
    {"threshold": "known amps", "plan": "18 (heard clean, measured as amps)", "now": 11,
     "why": "re-derived from the target-vs-DI measurements, less Passing Ships ElecGtr4 (review) and the 7 pairs whose "
            "DI sitting 1 rejected (re-review: a pair without a real DI cannot anchor a DI-to-amp calibration)"},
    {"threshold": "A2 slope (calibration fix)", "plan": None,
     "now": f"where the coherent A2 goes to the ear: target-minus-DI slope over 5-10 kHz > {A2_SLOPE_FAIL} dB/oct fails "
            f"(bleed under -30 dB only)",
     "why": "the real T0 calibration stopped (2026-10-23): the clean cab-off negative read a coherent drop of -2.0 and "
            "-2.8 dB over 12 and 7 bins (under the 17-bin gate: the ear), and A1 passed it on Morgan's 52-sample latency. "
            "A cab's top falls steeply; no cab keeps the DI's. The fail line is A2's 3.3 dB over two octaves; on the stored "
            "data the bleed-clean known amps read -10.5 to -24.2 dB/oct, the cab-off and Prodigal cases +0.0 to +10.9"},
    {"threshold": "A1_PROM_MIN", "plan": None, "now": A1_PROM_MIN,
     "why": "a lag is read only where the GCC peak stands out: the known amps' halves read prominence 24-279, the "
            "unreadable high-gain DI/amp pairs 4.4-6.7; under it A1 goes to the ear (no known case moves)"},
    {"threshold": "D4 (new, user 2026-10-23)", "plan": None, "now": f"crest < {D4_CREST_DB} dB or slope < {D4_SLOPE_MIN}",
     "why": "set on the user's 35 heard crop DIs (sitting 1): in-sample 30 of 35 agree, leave-one-out fewer (the "
            "calibration record); the ear decides heard DIs, and D4 alone never decides an unheard one (a flag queues "
            "it for the ear)"},
    {"threshold": "A1 band", "plan": "full band (the bleed audit's di_lag_ms)", "now": f"{LAG_BAND_HZ[0]:.0f}-{LAG_BAND_HZ[1]:.0f} Hz",
     "why": "on the 48 kHz crops the full-band GCC-PHAT reads 0 ms on several known amps (a zero-lag path above "
            "4 kHz); the band-limited lag agrees with the stored di_lag_ms (read at 24 kHz)"},
)

# --- calibration ---------------------------------------------------------------------------------------------
# The known amps come from the target-vs-DI measurements of 2026-10-23 (docs/audits/target-vs-di-2026-10-23), not
# from data-review-1's sitting 1 (which judged the DI clips): every part whose target follows its DI with a mic delay
# of 0.1-30 ms and whose |H| falls at least 12 dB from 0.5-2 kHz to 6-12 kHz in both halves (`known_amps_from`),
# less Passing Ships ElecGtr4 (its DI was heard as an amp in half B; dropped by the review) and less the pairs whose DI
# sitting 1 rejected (dropped by the re-review).
TVD_MEASURES = PLUGIN_ROOT / "docs/audits/target-vs-di-2026-10-23/measures.json"
KNOWN_RULE = {"lag_ms": (0.1, 30.0), "hf_drop_db": -12.0, "halves": 2}
# The re-review of #281 also drops every pair whose DI the user's ear rejected in sitting 1 (processed, an amp or a
# stem): a pair without a real DI cannot anchor a DI-to-amp calibration. 11 known amps remain; the fail line stands.
KNOWN_EAR_REJECTED = ("cambridge-Passing_Ships-ElecGtr6", "telefunken-Bloomlight-GTR", "telefunken-Farthest_Step-GTR",
                      "telefunken-First_Offering-GTR_2", "telefunken-Gym_Hours-GTR_2", "telefunken-Russian_Cream-GTR_2",
                      "telefunken-She's_Gone-GTR")
KNOWN_DROPPED = ("cambridge-Passing_Ships-ElecGtr4",) + KNOWN_EAR_REJECTED
KNOWN_AMPS = (
    "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr2", "cambridge-It_Was_My_Fault_For_Waiting-ElecGtr3",
    "cambridge-Signs-ElecGtr2", "cambridge-colour-me-red-elecgtr02", "cambridge-colour-me-red-elecgtr03",
    "cambridge-get-out-of-bed-elecgtr2", "cambridge-magilla-elecgtr1", "cambridge-magilla-elecgtr1dt",
    "cambridge-wickerman-elecgtr3", "telefunken-Blind_Spots-GTR", "telefunken-Sculptor's_Request-GTR_2")
KNOWN_FAILS = ("cambridge-Prodigal-ElecGtr3", "cambridge-Prodigal-ElecGtr5")
# The constructed negatives' DIs (both heard clean and passing D4): one whose HF stays coherent through its amp
# (It Was My Fault ElecGtr3) and one whose amp track is incoherent above 6 kHz (magilla elecgtr1).
NEG_SOURCES = ("cambridge-It_Was_My_Fault_For_Waiting-ElecGtr3", "cambridge-magilla-elecgtr1")
# The rendered negatives: kind -> (amp, start). The SW50R and AC20 clean cab-off renders were declared after the
# first real calibration failed and the A2 slope check was added (#282's review): fresh cases the check never saw.
NEG_RENDERS = {"cab_off_clean": ("pr12", "clean"), "cab_off_crunch": ("pr12", "crunch"),
               "cab_off_clean_sw50r": ("sw50r", "clean"), "cab_off_clean_ac20": ("ac20", "clean")}
NEG_KINDS = ("copy", "eq") + tuple(NEG_RENDERS)
NEG_DECLARED = {"copy": "the DI itself", "eq": "the DI through a cab-like linear EQ, delayed 1.5 ms",
                "cab_off_clean": "the DI through Morgan PR12 (clean start), cab section off",
                "cab_off_crunch": "beside: the DI through Morgan PR12 (crunch start), cab section off",
                "cab_off_clean_sw50r": "fresh (declared after the slope check): SW50R (clean start), cab section off",
                "cab_off_clean_ac20": "fresh (declared after the slope check): AC20 (clean start), cab section off"}
NEG_MUST_FAIL = {"copy": ("A1", "A3", "A4"), "eq": ("A3",), "cab_off_clean": ("A2",),
                 "cab_off_clean_sw50r": ("A2",), "cab_off_clean_ac20": ("A2",)}   # any one of these must fail
NEG_LEVEL_LUFS = -22.9
NEG_EQ = {"band_hz": (80.0, 5000.0), "order": 4, "peak_hz": 2000.0, "peak_q": 1.5, "peak_gain": 1.0, "delay_ms": 1.5,
          "gain": 0.5}
# The two conflicts of decision 2 (Quicksand ElecGtr2, Today's The Day ElecGtr07) fail measures (A6; A5): their measured
# fails stand (the user, 2026-10-24), so they are excluded like any measured fail and not queued.

# --- the stem scan ---------------------------------------------------------------------------------------------
STEM_TAKE_DB = -30.0                  # a stem passes when every guitar track of its session reads under this
STRICT_LEVELS = (-35.0, -40.0)
STRICT_DETECT_TOL = 3.0               # an injected take at L must read at least L - 3 dB
STRICT_BASE_MARGIN = 5.0              # ... and the uninjected track under L - 5 dB
REMOVED = "Kimock and Swatkins stay out of K (set by the ML session, 2026-10-23; the user may overrule)"
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


def a2_half_status(drop_db, n_lo, n_hi, min_bins=A2_MIN_BINS, pass_db=A2_PASS_DB, fail_db=A2_FAIL_DB):
    """One half's A2, decided only over min_bins coherent bins in both bands (the re-review's ruling: a fail must
    pass the same gate as a pass): pass at pass_db or more, fail under fail_db; otherwise (between the two, or too
    few coherent bins) the ear, which keeps the part out until heard."""
    if drop_db is None or (n_lo or 0) < min_bins or (n_hi or 0) < min_bins:
        return "ear"
    if drop_db < fail_db:
        return "fail"
    return "pass" if drop_db >= pass_db else "ear"


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


def target_verdict(st, ear_clean, ear_amp, in_mix=False):
    """A target's standing. st: {measure: status}; ear_clean: True/False/None (both halves heard clean on
    data-review-1); ear_amp: True/False/None (heard as an amp on the target-vs-DI page).
    -> (verdict, reasons): 'verified', 'excluded' (a measured fail, or the ear said no) or 'pending ear'."""
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
    return ("pending ear", why) if why else ("verified", [])


def d1_status(halves, prom_min=A1_PROM_MIN, min_bins=A2_MIN_BINS, pass_db=A2_PASS_DB, fail_db=A2_FAIL_DB):
    """D1 over a DI's sections (a chain property, read robustly): A1 on the median of its readable lags (GCC
    prominence >= prom_min); A2 on the median drop of its halves with min_bins coherent bins in both bands: fail under
    fail_db, pass at pass_db, else (or none such) the ear. halves: [{"lag_ms", "lag_prominence", "a2": {...}}].
    -> {"status", "A1", "A2", "lag_ms", "drop_db", "n_lags", "n_drops"}."""
    lags = [h["lag_ms"] for h in halves if (h.get("lag_prominence") or 0) >= prom_min]
    full = [h["a2"]["drop_db"] for h in halves if h["a2"]["drop_db"] is not None
            and (h["a2"]["n_lo"] or 0) >= min_bins and (h["a2"]["n_hi"] or 0) >= min_bins]
    lag = statistics.median(lags) if lags else None
    drop = statistics.median(full) if full else None
    a1 = a1_status(lag) if lags else "ear"
    if drop is not None and drop < fail_db:              # both a fail and a pass need the 17-bin gate
        a2 = "fail"
    elif drop is not None and drop >= pass_db:
        a2 = "pass"
    else:
        a2 = "ear"
    drops = full
    status = "fail" if "fail" in (a1, a2) else ("pass" if (a1, a2) == ("pass", "pass") else "ear")
    return {"status": status, "A1": a1, "A2": a2, "lag_ms": lag, "drop_db": drop, "n_lags": len(lags),
            "n_drops": len(drops)}


def di_verdict(st):
    """A DI's standing: 'excluded' on a measured fail of D1-D3 (D4 alone never excludes an unheard DI); 'pending ear'
    when D1 went to the ear, when the DI has no amp track (DI-only: D1 not measurable), or when D4 flags it; else
    'verified'. -> (verdict, reasons)."""
    fails = [m for m in ("D1", "D2", "D3") if st.get(m) == "fail"]
    if fails:
        return "excluded", [f"{m} fails" for m in fails]
    why = []
    if st.get("D1") == "ear":
        why.append("D1 to the ear")
    elif st.get("D1") is None:
        why.append("DI-only: D1 not measurable")
    if st.get("D4") == "fail":
        why.append("D4 flags it (processed?)")
    return ("pending ear", why) if why else ("verified", [])


def d4_status(crest_db, bright_slope, crest_min=D4_CREST_DB, slope_min=D4_SLOPE_MIN):
    """The DI-is-unprocessed check: 'fail' (reads as processed: drive or compression) when the median frame crest
    factor is under crest_min or the brightness does not rise with level; None readings fail closed."""
    if crest_db is None or bright_slope is None:
        return "fail"
    return "fail" if crest_db < crest_min or bright_slope < slope_min else "pass"


def merge_ear(values, positive):
    """Several answers on one item: any answer other than `positive` and 'unsure' wins (False); all `positive` is
    True; otherwise (unsure, or nothing) None."""
    vs = [v for v in values if v is not None]
    if any(v not in (positive, "unsure") for v in vs):
        return False
    return True if vs and all(v == positive for v in vs) else None


def d4_fit(rows, grid=D4_GRID):
    """D4's OR rule (crest under c, or slope under s) that best separates heard-processed from heard-clean DIs: the
    most (caught - flagged), then the most caught, then the lowest (c, s). rows: [(ear_clean, crest, slope)].
    -> (c, s, caught, flagged)."""
    import numpy as np

    best = None
    cs = np.round(np.arange(grid["crest"][0], grid["crest"][1] + 1e-9, grid["crest"][2]), 4)
    ss_ = np.round(np.arange(grid["slope"][0], grid["slope"][1] + 1e-9, grid["slope"][2]), 4)
    for c in cs:
        for sl in ss_:
            tp = sum(1 for e, cr, s_ in rows if e is False and (cr < c or s_ < sl))
            fp = sum(1 for e, cr, s_ in rows if e is True and (cr < c or s_ < sl))
            key = (tp - fp, tp, -c, -sl)
            if best is None or key > best[0]:
                best = (key, float(c), float(sl), tp, fp)
    return best[1], best[2], best[3], best[4]


def d4_loo(rows, grid=D4_GRID):
    """Leave-one-out agreement of D4's rule search with the ear: each heard DI judged by the rule fitted on the
    others. -> (agreeing, heard)."""
    ok = 0
    for i, (e, cr, sl) in enumerate(rows):
        c, s_, _, _ = d4_fit(rows[:i] + rows[i + 1:], grid)
        ok += (cr < c or sl < s_) == (e is False)
    return ok, len(rows)


def overlaps(a0, a1, b0, b1):
    return a0 < b1 and b0 < a1


def covers(a, b, start_s, dur=CROP_S, tol=1e-6):
    """A heard window [a, b] covers the whole section at start_s: only then can a clean answer clear it."""
    return a <= start_s + tol and b >= start_s + dur - tol


def known_amps_from(measures, rule=KNOWN_RULE, dropped=KNOWN_DROPPED, fails=None):
    """The calibration's known amps from the target-vs-DI measurements: both halves with a mic delay in range and
    the |H| roll-off at least the rule's (hf_drop_H <= -12 dB), less the dropped parts and the known fails."""
    fails = set(KNOWN_FAILS if fails is None else fails)
    sr = measures.get("sample_rate", SR)
    out = []
    for slug, v in sorted(measures["parts"].items()):
        hs = v["halves"]
        if len(hs) < rule["halves"] or slug in dropped or slug in fails:
            continue
        if all(rule["lag_ms"][0] <= 1000.0 * h["lag"] / sr <= rule["lag_ms"][1] and h["hf_drop_H"] <= rule["hf_drop_db"]
               for h in hs.values()):
            out.append(slug)
    return tuple(out)


def ear_di_verdict(halves):
    """The user's ear on a crop's DI (data-review-1, sitting 1: the DI clip): True when every answer on every heard
    half is 'clean', False when any is not (processed, an amp, another guitar: a negative wins), None when unheard.
    halves: {half: verdict or [verdicts]}."""
    vs = []
    for v in halves.values():
        vs += v if isinstance(v, list) else [v]
    return merge_ear(vs, "clean")


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
        out["halves"][h] = {"lag_ms": round(lag, 3), "lag_prominence": round(prom, 1), "a2": cab_drop(di[s], ref[s], sr),
                            "slope": rel_hf_slope(di[s], ref[s], sr)}
    lags = [out["halves"][h]["lag_ms"] for h in halves if out["playing"].get(h)]
    lag_c, _ = gcc_lag_ms(di[int(halves["A"][0] * sr):], ref[int(halves["A"][0] * sr):], sr)
    out["lag_ms_crop"] = round(lag_c, 3)
    out["a3"] = linear_residuals(di, ref, sr, lags[0] if len(lags) == 1 else lag_c, playing=out["playing"])
    return out


def hf_slope(x, sr=SR, band=A2_SLOPE_BAND_HZ, nper=A2_NPERSEG):
    """The spectral slope (dB per octave) of x over `band`: a least-squares line through its Welch PSD in dB against
    log2 frequency. None for a silent signal."""
    import numpy as np
    import scipy.signal as ss

    f, P = ss.welch(np.asarray(x, np.float64), sr, nperseg=nper)
    m = (f >= band[0]) & (f <= band[1])
    if not m.any() or not np.any(P[m] > 0):
        return None
    return float(np.polyfit(np.log2(f[m]), 10 * np.log10(P[m] + 1e-30), 1)[0])


def rel_hf_slope(di, ref, sr=SR):
    """A2's coherence-free reading: {"target", "di", "rel"} slopes over 5-10 kHz (dB/oct), rel = target - DI."""
    t, d = hf_slope(ref, sr), hf_slope(di, sr)
    return {"target": t, "di": d, "rel": None if t is None or d is None else t - d}


def a2_slope_fails(rel, bleed_db, fail=A2_SLOPE_FAIL, bleed_max=A6_BLEED_DB):
    """The cab check without coherence: a target whose top falls no faster than its DI's (rel above `fail`) has no
    cab. Read only on a half known clean of bleed (bleed_db under bleed_max; None: no reading, no opinion)."""
    return rel is not None and bleed_db is not None and bleed_db < bleed_max and rel > fail


def pair_status(m, max_corr=None, same_hash=False, bleed=None):
    """A1-A4 statuses of a `measure_pair` reading over its playing halves (A4 from the copy check, when given);
    with no playing half every measure fails (fail closed). bleed: {half: bleed dB} where known (the bleed audit's;
    constructed negatives carry none, -99): where the coherent A2 goes to the ear, the relative HF slope can fail it."""
    hs = {h: v for h, v in m["halves"].items() if m.get("playing", {}).get(h, True)}
    a1 = combine_part([a1_status(v["lag_ms"], prominence=v.get("lag_prominence")) for v in hs.values()])

    def a2h(h, v):
        st = a2_half_status(v["a2"]["drop_db"], v["a2"]["n_lo"], v["a2"]["n_hi"])
        rel = (v.get("slope") or {}).get("rel")
        return "fail" if st == "ear" and a2_slope_fails(rel, (bleed or {}).get(h)) else st

    a2 = a2_part([a2h(h, v) for h, v in hs.items()])
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
    """{di id: {"datasets", "band", "sections": [{id, start_s, own}]}} for part C's D build (pool and V_sep sections,
    own=True), every DI of those sessions at every other D-build section time of its session (own=False: the windows
    where it plays as another guitar in a self-built mix, so every window a mix can use is measured), and the
    sessions' other inventory DIs at those times and at up to 4 of their own clean sections. -> (scope, Meta)."""
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
        d["sections"].append({"id": sid, "start_s": float(sec["start_s"]), "own": True})
        times.setdefault(meta.inv[sec["di"]]["session_dir"], set()).add(float(sec["start_s"]))
    for di, d in out.items():                            # a D-build DI as another guitar: the session's other times
        have = {round(x["start_s"], 1) for x in d["sections"]}
        d["sections"] += [{"id": f"{di}@{t:.1f}", "start_s": t, "own": False}
                          for t in sorted(times[meta.inv[di]["session_dir"]]) if round(t, 1) not in have]
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
                   "sections": [{"id": f"{di}@{t:.1f}", "start_s": t, "own": False} for t in ts]}
    return out, meta


# --- commands: calibration ---------------------------------------------------------------------------------------

def neg_dir(root):
    return root / "calibration" / "negatives"


def cmd_negatives(args):
    """The cab-off negatives (renders): each source crop's DI, levelled to -22.9 LUFS by one gain (no EQ, so the
    target is the amp alone), through `NEG_RENDERS` (PR12 clean and crunch; SW50R and AC20 clean, the fresh pair)
    with the cab section off; one process, isolate=True, a discarded priming render per (DI, amp): 8 renders plus 6
    priming from scratch (the PR12 four were stored first, with 2 priming). Never overwrites a stored negative."""
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
    todo = sorted(((s, k) for s in NEG_SOURCES for k in NEG_RENDERS if f"{s}|{k}" not in man["renders"]),
                  key=lambda sk: (sk[0], NEG_RENDERS[sk[1]][0], sk[1]))
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
            amp, base = NEG_RENDERS[kind]
            sel, S = menu[amp][K.START[base][amp]]
            x = dict(S)
            x[("cabParameters", "sectionActive")] = "false"
            crop = pathlib.Path(lt[slug]["crop"])
            di = mono(crop / "di.wav")
            di = DC_.to_lufs(di, NEG_LEVEL_LUFS)
            lead = int(round(PS.TRIM_S * SR))
            di32 = np.concatenate([np.zeros(lead), di]).astype(np.float32)
            if last != (slug, amp):                             # a new DI or amp: prime
                rr.render(di32, sel, x)                         # priming, discarded (a new DI)
                man["primes"] += 1
                n0 += 1
            last = (slug, amp)
            y = np.asarray(rr.render(di32, sel, x), np.float64)
            n0 += 1
            y = (y.mean(axis=1) if y.ndim == 2 else y)[lead:lead + len(di)]
            peak = float(np.max(np.abs(y[int(0.25 * SR):]))) if len(y) else 0.0
            if not np.isfinite(y).all() or peak < 1e-3:
                raise SystemExit(f"{slug} {kind}: the cab-off render is silent or non-finite (peak {peak:.2e})")
            p = nd / f"{slug}__{kind}.flac"
            scale, sha = G.write_flac(p, y, SR)
            man["renders"][f"{slug}|{kind}"] = {"path": str(p), "scale": scale, "sha256": sha, "amp": amp,
                                                "start": K.START[base][amp], "cab": "off", "level_lufs": NEG_LEVEL_LUFS,
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
    """Calibration (zero renders): the 11 known amps (re-derived from the target-vs-DI measurements, checked here), the
    2 known fails and the constructed negatives through A1-A4; CALIBRATION OK iff the known amps fail nothing, the
    known fails fail something and each declared negative fails its measure. D4 against the user's ear (`--ear-di`,
    required): the agreement in-sample and leave-one-out. Never overwrites an OK record."""
    import numpy as np

    from learn import direct_sound_gate as G

    require_real(args)
    root = out_root(args)
    path = root / "calibration" / "calibration.json"
    if (_load(path) or {}).get("verdict") == "OK" and not args.smoke:
        raise SystemExit(f"{path} reads OK: a rerun needs review; move it aside by hand first")
    lt = label_table()
    heldout_ok(KNOWN_AMPS + KNOWN_FAILS + NEG_SOURCES)
    derived = known_amps_from(json.loads(TVD_MEASURES.read_text()))
    if tuple(sorted(derived)) != tuple(sorted(KNOWN_AMPS)):
        raise SystemExit(f"KNOWN_AMPS differs from the target-vs-DI derivation: {sorted(set(derived) ^ set(KNOWN_AMPS))}")
    if not args.ear_di and not args.smoke:
        raise SystemExit("calibrate needs --ear-di (the sitting-1 export): D4 is calibrated on the user's ear")
    bt = json.loads(BLEED_TABLE.read_text())
    man = _load(neg_dir(root) / "negatives.json") or {"renders": {}}
    rows = []

    def row(name, kind, di, ref, crop=None, bleed=None):
        m = measure_pair(di, ref)
        if crop is not None:
            rec, base, cpart, dis, _ = crop_session(crop)
            mc, same, corr = _copy_check(crop, ref, rec, base, cpart, dis)
        else:
            mc, same, corr = max_copy_corr(ref, {"own DI": di}, SR)["own DI"], False, None
        st = pair_status(m, mc, same, bleed)
        r = {"name": name, "kind": kind, "status": st, "readings": m, "a4_max_corr": mc, "a4_same_hash": same, "bleed": bleed,
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
        bh = (bt.get(slug) or {}).get("halves") or {}
        r = row(slug, "known" if slug in KNOWN_AMPS else "fail", mono(crop / "di.wav"), mono(crop / "reference.wav"), crop,
                {h: (bh.get(h) or {}).get("bleed_db") for h in HALVES})
        r["stored_di_lag_ms"] = (bt.get(slug) or {}).get("di_lag_ms")
    missing = []
    for slug in NEG_SOURCES:
        crop = pathlib.Path(lt[slug]["crop"])
        di = mono(crop / "di.wav")
        clean = {h: -99.0 for h in HALVES}                  # constructed: no bleed by construction
        row(f"{slug}|copy", "copy", di, di.copy(), bleed=clean)
        row(f"{slug}|eq", "eq", di, neg_eq(di, SR), bleed=clean)
        for kind in NEG_RENDERS:
            v = man["renders"].get(f"{slug}|{kind}")
            if v is None:
                missing.append(f"{slug}|{kind}")
                continue
            y = G.read_flac(pathlib.Path(v["path"]), v["scale"], v["sha256"])
            row(f"{slug}|{kind}", kind, di, np.asarray(y, np.float64), bleed=clean)
    # D4 against the user's ear on the crops' DIs (sitting 1 of data-review-1, judged on the DI clip)
    d4 = None
    if args.ear_di:
        di_ear = ear_answers([], args.ear_di)["crop_di"]
        heard = {slug: ear_di_verdict(h) for slug, h in di_ear.items() if slug in lt}
        meas, readings = {}, {}
        for slug in sorted(heard):
            f = di_processing(mono(pathlib.Path(lt[slug]["crop"]) / "di.wav")[int(HALVES["A"][0] * SR):])
            readings[slug] = {**f, "ear_clean": heard[slug]}
            meas[slug] = d4_status(f["crest_db"], f["bright_slope"])
        fit_rows = [(heard[s_], readings[s_]["crest_db"], readings[s_]["bright_slope"]) for s_ in sorted(heard)
                    if heard[s_] is not None and readings[s_]["crest_db"] is not None]
        loo, n_loo = d4_loo(fit_rows)
        refit = d4_fit(fit_rows)
        d4 = {"agreement": d4_agreement(heard, meas), "leave_one_out": {"agree": loo, "heard": n_loo},
              "refit_on_all": {"crest_db": refit[0], "slope_min": refit[1], "caught": refit[2], "flagged": refit[3]},
              "readings": readings, "thresholds": {"crest_db": D4_CREST_DB, "bright_slope": D4_SLOPE_MIN}}
        a = d4["agreement"]
        print(f"D4 against the ear: in-sample {a['agree']}/{a['heard']}, leave-one-out {loo}/{n_loo}; processed "
              f"missed {a['processed_missed']}; clean flagged (conflicts for the ear) {a['clean_flagged']}")
    verdict, probs = calibration_verdict(rows)
    if missing:
        probs.append(f"negatives not rendered: {missing} (run `negatives`)")
        verdict = "FAIL"

    def a2_val(r):
        ds = [r["readings"]["halves"][h]["a2"]["drop_db"] for h in "AB"
              if r["readings"]["halves"][h]["a2"]["drop_db"] is not None and r["readings"]["halves"][h]["a2"]["n_hi"]]
        return min(ds) if r["kind"] == "known" and ds else (max(ds) if ds else None)

    rec = {"plan": PLAN, "design": DESIGN, "smoke": bool(args.smoke), "verdict": verdict, "problems": probs,
           "thresholds": thresholds(), "threshold_moves": list(THRESHOLD_MOVES), "negatives": NEG_DECLARED,
           "must_fail": {k: list(v) for k, v in NEG_MUST_FAIL.items()},
           "known_amps": {"rule": KNOWN_RULE, "dropped": list(KNOWN_DROPPED), "ear_rejected": list(KNOWN_EAR_REJECTED),
                          "source": str(TVD_MEASURES.name),
                          "parts": list(KNOWN_AMPS)},
           "margins": [margins(rows, "A2 drop (halves with coherent bins)", a2_val,
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
                   "min_bins": A2_MIN_BINS, "pass_db": A2_PASS_DB, "fail_db": A2_FAIL_DB,
                   "slope_band_hz": list(A2_SLOPE_BAND_HZ), "slope_fail_db_oct": A2_SLOPE_FAIL},
            "A3": {"sr": A3_SR, "pre_ms": A3_PRE_MS, "post_ms": A3_POST_MS, "ridge": A3_RIDGE, "max_db": A3_MAX_DB},
            "A4": {"max_corr": A4_MAX_CORR, "lag_ms": A4_LAG_MS},
            "A5": {"play_min": A5_PLAY_MIN, "chroma_min": A5_CHROMA_MIN, "onset_min": A5_ONSET_MIN},
            "measure_play_min": MEASURE_PLAY_MIN,
            "D4": {"crest_db": D4_CREST_DB, "slope_min": D4_SLOPE_MIN, "sample_seed": D4_SAMPLE_SEED},
            "A6": {"bleed_db": A6_BLEED_DB, "mix_take_db": A6_TAKE_DB},
            "stems": {"take_db": STEM_TAKE_DB, "strict_levels": list(STRICT_LEVELS)}}


def calibration_ok(root):
    """An OK calibration under today's thresholds, negatives, must-fail rule and known amps (an OK made before any of
    them changed does not count)."""
    rec = _load(root / "calibration" / "calibration.json") or {}
    same = (rec.get("thresholds") == thresholds() and rec.get("negatives") == NEG_DECLARED
            and rec.get("must_fail") == {k: list(v) for k, v in NEG_MUST_FAIL.items()}
            and (rec.get("known_amps") or {}).get("parts") == list(KNOWN_AMPS))
    return rec.get("verdict") == "OK" and same and not rec.get("smoke"), rec


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
    prev = _load(path) or {}
    if prev and prev.get("thresholds") != thresholds():
        raise SystemExit(f"{path} was measured under other thresholds: move it aside by hand (no silent resume)")
    done = prev.get("parts", {})
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
        windows = None
        if not any(m["playing"].values()) and "level prior" in uses:
            windows = session_windows(slug, base, cpart)          # the crop is silent: read the prior's sections
        bh = (bt.get(slug) or {}).get("halves") or {}
        mix = None
        if slug in stage_f:
            own_x = [cpart["reference"], *(cpart.get("alternate") or []), *(cpart.get("simulated") or [])]
            mix = same_part_in_mix(crop, rec, base, di, ref, own_x)
        row = {"uses": uses, "band": lt[slug]["band"], "gain_class": lt[slug]["gain_class"],
               "readings": m, "a4_max_corr": mc, "a4_same_hash": same, "a4_corr": corr, "a5": a5,
               "bleed": {h: {"flag": (bh.get(h) or {}).get("flag"), "bleed_db": (bh.get(h) or {}).get("bleed_db")}
                         for h in HALVES},
               "bleed_db": {h: (bh.get(h) or {}).get("bleed_db") for h in HALVES},
               "stored_di_lag_ms": (bt.get(slug) or {}).get("di_lag_ms"), "mix_same_part": mix,
               "session_windows": windows, "in_mix": slug in stage_f,
               "crop_start_s": float(rec.get("excerpt_start_s", 0.0))}
        row["status"] = target_status(row)
        done[slug] = row
        _save(path, {"plan": PLAN, "smoke": bool(args.smoke), "thresholds": thresholds(), "parts": done,
                     "scope": sorted(scope), "complete": False, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"{k + 1}/{len(scope)} {slug[:50]:50s} {row['status']}", flush=True)
    _save(path, {"plan": PLAN, "smoke": bool(args.smoke), "thresholds": thresholds(), "parts": done,
                 "scope": sorted(scope), "complete": set(done) >= set(scope), "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"TARGETS DONE: {len(done)} parts")


def target_status(row):
    """A1-A6 of a stored target row, recomputed from its readings under the current thresholds (`lists` re-reads
    every verdict this way). A6's mix clause counts only electric same-part tracks."""
    st = pair_status(row["readings"], bleed={h: ((row.get("bleed") or {}).get(h) or {}).get("bleed_db") for h in HALVES})
    st["A4"] = a4_status(row.get("a4_max_corr"), row.get("a4_same_hash", False))
    w = row.get("session_windows")
    if w and w.get("readings"):
        sts = [pair_status(x["readings"]) for x in w["readings"]]
        st.update({"A1": combine_part([x["A1"] for x in sts]), "A2": a2_part([x["A2"] for x in sts]),
                   "A3": combine_part([x["A3"] for x in sts])})
    st["A5"] = combine_part([a5_half_status(v["di_play_share"], v["chroma"], v["onset"]) for v in row["a5"].values()])
    st["A6"] = combine_part([a6_half_status((row.get("bleed") or {}).get(h)) for h in HALVES])
    if row.get("in_mix"):
        mix = row.get("mix_same_part")
        st["A6mix"] = None if mix is None else a6_mix_status(
            [v["power_db"] for t, hh in mix.items() for v in hh.values() if v["same_part"] and is_electric_take(t)])
    return st


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

    from learn import clean_di as CD

    require_real(args)
    root = out_root(args)
    k, n = args.shard
    scope, meta = di_scope()
    man_rows = json.loads(PS.MANIFEST.read_text())["sections"]
    lt = label_table()
    crops = {s: u for s, u in target_scope().items() if s in lt}
    heldout_ok(crops)                                   # the crops: the data-review page's fail-closed check
    for d in scope:                                     # every inventory DI read here: part A's held-out refusal
        CD.refuse_held_out(meta.inv[d])
    all_jobs = [("di", d) for d in sorted(scope)] + [("crop", s) for s in sorted(crops)]
    jobs = [j for i, j in enumerate(all_jobs) if i % n == k][:args.limit or None]
    path = root / "t0" / f"dis-{k}of{n}.json"
    prev = _load(path) or {}
    if prev and prev.get("thresholds") != thresholds():
        raise SystemExit(f"{path} was measured under other thresholds: move it aside by hand (no silent resume)")
    done = prev.get("rows", {})
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
                d2 = {"flags": mf[0], "tags": mf[1], "source": src}
                d4 = di_processing(di)
                secs.append({"section": s["id"], "start_s": s["start_s"], "own": s.get("own", True), "D1": d1, "D2": d2,
                             "D4": d4})
            row = {"di": key, "band": scope[key]["band"], "datasets": scope[key]["datasets"], "amp_tracks": amps,
                   "hum_suspect": key in PS.HUM_SUSPECT, "path": rec["path"], "sections": secs}
            row.update(di_row_status(row))
            done[f"{kind}:{key}"] = row
        else:
            crop = pathlib.Path(lt[key]["crop"])
            rec, base, cpart, dis, _ = crop_session(crop)
            di_path = base / cpart["di"]
            t0 = float(rec.get("excerpt_start_s", 0.0))
            flags, tags, row = window_d2(di_path, t0)
            src = next((r for r in meta.inv.values() if r.get("slug") == key), None)
            suspect = bool(src) and src["id"] in PS.HUM_SUSPECT
            d4 = di_processing(mono(crop / "di.wav")[int(HALVES["A"][0] * SR):])
            crow = {"slug": key, "uses": crops[key], "di_file": str(di_path), "di_name": cpart["di"], "window_s": t0,
                    "d2": {"flags": flags, "tags": tags, "row": row, "hum_suspect": suspect},
                    "d4": d4, "inventory_di": src["id"] if src else None}
            crow["status"] = crop_status(crow)                   # D1 for a crop is its target's A1-A2 (targets)
            done[f"{kind}:{key}"] = crow
        _save(path, {"plan": PLAN, "smoke": bool(args.smoke), "shard": [k, n], "thresholds": thresholds(),
                     "jobs": len(jobs), "complete": False, "rows": done, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"{m + 1}/{len(jobs)} {kind} {key[-60:]}: {done[f'{kind}:{key}']['status']}", flush=True)
    _save(path, {"plan": PLAN, "smoke": bool(args.smoke), "shard": [k, n], "thresholds": thresholds(), "jobs": len(jobs),
                 "complete": all(f"{a}:{b}" in done for a, b in jobs) and not args.limit, "rows": done,
                 "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"DIS DONE {k}/{n}")


def di_row_status(row):
    """A pool, V_sep or other-guitar DI's statuses, recomputed from its stored readings under the current thresholds:
    D1 over every measured window (None for a DI-only part); D2 over its own D-build sections (hum-suspect DIs fail),
    and per window; D3 by name; per window D4 ('silent' where the DI does not play; D4 never excludes alone).
    -> {"status", "d1", "d4_sections", "d2_sections"}."""
    secs = row["sections"]
    d1 = d1_status([h for x in secs if x["D1"] for h in x["D1"]["halves"].values()]) if row.get("amp_tracks") else None
    d2w = {x["section"]: d2_status(x["D2"]["flags"], row.get("hum_suspect", False)) for x in secs}
    own = [x["section"] for x in secs if x.get("own", True)]
    d2 = combine_part([d2w[k] for k in own]) if own else ("fail" if row.get("hum_suspect") else "pass")
    d4 = {x["section"]: ("silent" if x["D4"]["crest_db"] is None else d4_status(x["D4"]["crest_db"], x["D4"]["bright_slope"]))
          for x in secs}
    return {"status": {"D1": None if d1 is None else d1["status"], "D2": d2, "D3": d3_status(row["di"])},
            "d1": d1, "d4_sections": d4, "d2_sections": d2w}


def crop_status(row):
    """A crop's measure DI: D2 on the crop window (flags, hum-suspect), D3 by name, D4 on the crop window."""
    d2 = row["d2"]
    return {"D2": d2_status(d2["flags"], d2.get("hum_suspect", False)), "D3": d3_status(row.get("di_name") or row["di_file"]),
            "D4": d4_status(row["d4"]["crest_db"], row["d4"]["bright_slope"])}


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
    prev = _load(path) or {}
    if prev and prev.get("floor_db") != floor:
        raise SystemExit(f"{path} was scanned at another floor: move it aside by hand (no silent resume)")
    done = prev.get("sessions", {})
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
        _save(path, {"plan": PLAN, "smoke": bool(args.smoke), "shard": [k, n], "floor_db": floor, "complete": False,
                     "sessions": done, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        bad = [f for f, v in done[sd]["stems"].items() if not v["pass"]]
        print(f"{m + 1}/{len(jobs)} {pathlib.Path(sd).name}: {len(stems)} stems, {len(gtr)} guitar tracks, "
              f"failing {bad} ({time.time() - t:.0f} s)", flush=True)
    _save(path, {"plan": PLAN, "smoke": bool(args.smoke), "shard": [k, n], "floor_db": floor,
                 "complete": all(s_ in done for s_ in jobs) and not (args.limit or args.only), "sessions": done,
                 "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"STEM SCAN DONE {k}/{n} (floor {floor:.0f} dB)")


def scope_dis(dis):
    return sorted(dis)


# --- commands: the lists -----------------------------------------------------------------------------------------

EAR_PAGE = "trusted-data-ear"          # the listening page built from `ear-queue.json`
EAR_VERDICTS = {"target": ("clean_amp", "bleed", "other_guitar", "not_amp", "unsure"),
                "di": ("clean", "processed", "not_a_di", "hum", "unsure"),
                "di_amp": ("amp", "same_di", "processed", "unsure"),
                "stem": ("clean", "guitar", "unsure")}


def item_id(kind, key, start_s=None):
    return "ear-" + hashlib.sha1(f"{kind}|{key}|{start_s}".encode()).hexdigest()[:12]


def ear_answers(paths, di_paths=(), registry=None):
    """The user's ear. -> {"target_clean": {(slug, half): [verdicts]}, "target_amp": {slug: [verdicts]},
    "crop_di": {slug: {half: [verdicts]}}, "di_windows": {key: [(start_s, end_s, verdict)]}, "di_pairs": {di: [verdicts]}}.
    - `di_paths`: data-review-1 exports judged on the DI clip (sitting 1: 'clean' is a clean, unprocessed DI);
    - `paths`: target judgments: the target-vs-DI page ('amp' or not) and the ear-queue page (`EAR_PAGE`, its ids
      decoded through `registry`, the items `lists` has queued). A data-review-1 export is refused here (its amp
      items were judged on the DI clip). Several answers on one item are all kept; `merge_ear` lets a negative win.
    An ear-page export holds every item of its part, each stamped with the time the listener last touched it (`t`;
    null on a card never touched in that browser). On one item the latest touch across all exports stands: a changed
    answer replaces the old one, and an answer taken back (a null verdict with a time) clears it. A card never touched
    holds no answer, so an export from another browser or a rebuilt page never erases one. Notes go to `notes`, with
    or without a verdict, for the ML session to read before T1."""
    out = {"target_clean": {}, "target_amp": {}, "crop_di": {}, "di_windows": {}, "di_pairs": {}, "stems": {},
           "notes": [], "superseded": 0}
    registry = registry or {}
    pages = {"data-review-1": HOME / "listening/data-review-1/items.json",
             "target-vs-di-check": HOME / "listening/target-vs-di-check/items.json"}
    items = {}
    for page, p in pages.items():
        if p.exists():
            for it in json.loads(p.read_text())["items"]:
                items[it["id"]] = it
    loaded = []
    for p, about_di in [(q, False) for q in paths or ()] + [(q, True) for q in di_paths or ()]:
        d = json.loads(pathlib.Path(p).expanduser().read_text())
        page = d.get("page")
        if about_di and page != "data-review-1":
            raise SystemExit(f"{p}: --ear-di takes data-review-1 exports only (page {page})")
        if not about_di and page == "data-review-1":
            raise SystemExit(f"{p}: a data-review-1 export judged the DI clips; pass it as --ear-di, not --ear")
        if not about_di and page not in ("target-vs-di-check", EAR_PAGE):
            raise SystemExit(f"{p}: unknown page {page}")
        loaded.append((p, page, d))
    latest = {}                                     # ear-page item id -> (touch time, file order) of the answer that stands
    for n, (p, page, d) in enumerate(loaded):
        if page == EAR_PAGE:
            for a in d.get("answers") or []:
                t = answer_time(a, d)
                if t and (a["id"] not in latest or (t, n) >= latest[a["id"]]):
                    latest[a["id"]] = (t, n)
    for n, (p, page, d) in enumerate(loaded):
        for a in d.get("answers") or []:
            v = a.get("verdict")
            if page == EAR_PAGE and latest.get(a["id"], (None, None))[1] != n:
                out["superseded"] += bool(v)
                continue
            note = (a.get("note") or "").strip()
            src = registry.get(a["id"]) if page == EAR_PAGE else items.get(a["id"])
            if note:                                     # kept on retired cards too: the note may say why
                out["notes"].append({"file": str(p), "page": page, "id": a["id"], "verdict": v, "note": note,
                                     "retired": (src or {}).get("retired"), "kind": (src or {}).get("kind"),
                                     "key": (src or {}).get("key") or (src or {}).get("slug"), "title": a.get("title")})
            if not v:
                continue
            if page == EAR_PAGE:
                it = registry.get(a["id"])
                if it is None:
                    raise SystemExit(f"{p}: answer {a['id']} is not a queued item")
                if it.get("retired"):
                    print(f"{p}: skipping the answer on {a['id']}: {it['retired']}")
                    continue
                if v not in EAR_VERDICTS[it["family"]]:
                    raise SystemExit(f"{p}: {a['id']}: verdict {v} is not one of {EAR_VERDICTS[it['family']]}")
                if it["kind"] == "target":
                    out["target_clean"].setdefault((it["key"], it["half"]), []).append("clean" if v == "clean_amp" else v)
                    if v in ("clean_amp", "not_amp"):
                        out["target_amp"].setdefault(it["key"], []).append("amp" if v == "clean_amp" else "not_amp")
                elif it["kind"] == "di_amp":
                    out["di_pairs"].setdefault(it["key"], []).append(v)
                elif it["kind"] == "stem":
                    out["stems"].setdefault(it["key"], []).append(v)
                else:
                    out["di_windows"].setdefault(it["key"], []).append((it["start_s"], it["start_s"] + it["dur_s"], v))
                continue
            it = items.get(a["id"])
            if it is None:
                continue
            if page == "data-review-1" and it.get("section") == "amp":
                out["crop_di"].setdefault(it["slug"], {}).setdefault(it["half"], []).append(v)
            elif page == "target-vs-di-check":
                slug = (it.get("private") or {}).get("slug")
                if slug:
                    out["target_amp"].setdefault(slug, []).append(v)
    return out


def answer_time(a, d):
    """When the listener last touched an ear-page answer: its own `t`; an answer with a verdict but no `t` (a
    hand-made export) takes the export's time, or "0000" (before any real time) if it has none; an untouched card has
    none."""
    return a.get("t") or ((d.get("exported") or "0000") if a.get("verdict") else None)


def export_records(paths):
    """[{path, sha256, page, part, build, exported, answered}] of answer exports, as `lists` records them in
    verified.json. `answered`: {item id: touch time} of an ear-page export's touched cards."""
    out = []
    for p in paths or ():
        q = pathlib.Path(p).expanduser()
        d = json.loads(q.read_text())
        answered = {a["id"]: answer_time(a, d) for a in d.get("answers") or [] if answer_time(a, d)} \
            if d.get("page") == EAR_PAGE else None
        out.append({"path": str(q), "sha256": sha256_file(q), "page": d.get("page"), "part": d.get("part"),
                    "build": d.get("build"), "exported": d.get("exported"), "answered": answered})
    return out


def dropped_exports(prev, now):
    """The exports an earlier `lists` read that this run would drop. Each run rebuilds every verdict from the files it
    is given, so leaving one out loses its answers. An earlier export counts as kept when this run passes the same
    file (by sha256), or when this run's exports touched every card it touched, each as late or later (a later export
    from the same browser does; one from another browser usually doesn't). A record without `answered` (from before
    the per-card times) is kept only by the same file. prev: an earlier verified.json; now: `export_records` of this
    run. -> [paths]."""
    if not prev:
        return []
    old = prev.get("ear_exports")
    if old is None:                                       # a record from before 2026-10-23's review: paths only
        old = []
        for p in (prev.get("ear_files") or []) + (prev.get("ear_di_files") or []):
            q = pathlib.Path(p).expanduser()
            old.append({"path": str(q), "sha256": sha256_file(q) if q.exists() else None})
    shas = {e["sha256"] for e in now}
    touched = {}
    for n in now:
        for iid, t in (n.get("answered") or {}).items():
            touched[iid] = max(touched.get(iid, ""), t)
    out = []
    for e in old:
        if e.get("sha256") and e["sha256"] in shas:
            continue
        if e.get("answered") is not None and all(touched.get(iid, "") >= t for iid, t in e["answered"].items()):
            continue
        out.append(e["path"])
    return out


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
    """A target heard clean: False if any half was heard otherwise (any negative answer wins), True if every half was
    heard clean, None if a half is unheard. clean: {(slug, half): [verdicts]} (a bare verdict is one answer)."""
    vs = []
    for h in halves_used:
        a = clean.get((slug, h))
        vs.append(merge_ear(a if isinstance(a, list) else [a], "clean"))
    if any(v is False for v in vs):
        return False
    return True if all(v is True for v in vs) else None


def ear_amp_of(slug, amp):
    a = amp.get(slug)
    return merge_ear(a if isinstance(a, list) else [a], "amp")


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


def load_shards(root, prefix, key, check):
    """Every shard of a sharded command, merged. -> (merged rows, problems): a missing, incomplete or stale shard
    (`check(record)` false) is a problem; `lists` refuses on any."""
    files = sorted((root / "t0").glob(f"{prefix}-*of*.json"))
    if not files:
        return {}, [f"no {prefix} shard"]
    probs, have, ns = [], {}, set()
    for f in files:
        d = _load(f) or {}
        k, n = d.get("shard", (None, None))
        ns.add(n)
        have[k] = d
        if not d.get("complete"):
            probs.append(f"{f.name} is incomplete")
        if not check(d):
            probs.append(f"{f.name} was made under other thresholds or another floor")
    if len(ns) != 1:
        probs.append(f"{prefix} shards of different splits: {sorted(map(str, ns))}")
    else:
        n = ns.pop()
        missing = [k for k in range(n) if k not in have]
        if missing:
            probs.append(f"{prefix} shards missing: {missing} of {n}")
    out = {}
    for d in have.values():
        out.update(d.get(key, {}))
    return out, probs


def queue_item(kind, key, family, start_s, dur_s, paths, reason, **extra):
    return {"id": item_id(kind, key, start_s), "kind": kind, "family": family, "key": key, "start_s": start_s,
            "dur_s": dur_s, "paths": paths, "reason": reason, "verdicts": list(EAR_VERDICTS[family]), **extra}


def windows_of(key, ear, crop_rows):
    """Heard windows of a DI or crop key: [(start_s, end_s, verdict)], in the DI file's time. A crop's sitting-1 halves
    map to the crop's window (`build_data_review.HALF_CLIPS`); queue answers carry their own window."""
    from learn import build_data_review as BDR

    out = list(ear["di_windows"].get(key, []))
    for slug, cr in crop_rows.items():
        if key in (f"crop:{slug}", cr.get("inventory_di")):
            for h, vs in ear["crop_di"].get(slug, {}).items():
                a, b = BDR.HALF_CLIPS[h]
                out += [(cr["window_s"] + a, cr["window_s"] + b, v) for v in vs]
            out += [(s0, s1, v) for s0, s1, v in ear["di_windows"].get(f"crop:{slug}", [])
                    if key == cr.get("inventory_di")]
    return out


def section_ear(start_s, windows, dur=CROP_S):
    """The ear on one section: merged over the heard windows overlapping it (a negative wins)."""
    return merge_ear([v for a, b, v in windows if overlaps(start_s, start_s + dur, a, b)], "clean")


def busiest_audible(sections):
    """The section an ear item plays for a whole DI: audible first (D4 reads a crest), then the most playing frames.
    A digitally silent section counts every frame as playing (all sit within `play_db` of the max), so `frames`
    alone picks silence (15 items of the first ear queue, 2026-10-23)."""
    return max(sections, key=lambda x: (x["D4"]["crest_db"] is not None, x["D4"]["frames"] or 0))


def silent_items(registry, di_rows):
    """Queued DI windows that are digital silence (D4 reads no crest there). -> {item id}. Their answers carry no
    evidence, so `ear_answers` skips them."""
    out = set()
    for iid, it in registry.items():
        row = di_rows.get(it["key"]) if it["family"] in ("di", "di_amp") else None
        for x in (row or {}).get("sections", []):
            if abs(x["start_s"] - it["start_s"]) < 1e-6 and x["D4"]["crest_db"] is None:
                out.add(iid)
    return out


def quiet_windows(root):
    """DI windows `build_ear_page check --retire` found quiet (the DI hardly plays against its own file's level): their
    items are retired like silent ones, and their sections read 'silent' (no mix uses them, and they hold no DI back).
    -> (item ids, {(DI key, start_s rounded to 0.1)})."""
    items = (_load(root / "t0" / "quiet-items.json") or {}).get("items") or {}
    return set(items), {(v["key"], round(float(v["start_s"]), 1)) for v in items.values()}


def stem_activity(path, times, dur=CROP_S):
    """{start_s: the share of the window's frames that play against the file's own loudest (`clean_di.playing`)}."""
    import numpy as np

    from learn import clean_di as CD
    from learn import pretrain_set as PS

    fdb = CD.frame_db(PS.load_mono(path, PS.SR))
    play = CD.playing(fdb)
    out = {}
    for t in times:
        r = CD.frames_in(int(round(t * PS.SR)), int(round((t + dur) * PS.SR)), len(play))
        out[t] = float(np.mean(play[r.start:r.stop])) if len(r) else 0.0
    return out


def stem_risk(v):
    """A scanned stem's highest guitar take (dB; -inf when none was read): the nearest the floor is the riskiest."""
    vals = [float(x) for x in (v.get("takes_db") or {}).values() if x is not None]
    return max(vals) if vals else -math.inf


def pick_stem_checks(stems, di_rows, stored, activity=None, min_share=STEM_CHECK_MIN_SHARE, tries=STEM_CHECK_TRIES):
    """The stem spot-check (plan (f)'s T0 "spot-check stems by ear"; added to the sitting by the user, 2026-10-24): per
    scanned session, the passing stem nearest the floor (the highest guitar take; name order on a tie) that plays in
    one of the session's D-build section times, at its most active one. A stored choice is kept while its stem still
    passes, so the queue stays stable. -> {session dir: {"stem", "start_s", "share", "risk_db"} or {"none": why}}."""
    activity = activity or stem_activity
    out = {}
    for sd in sorted(stems):
        passing = {f: v for f, v in stems[sd]["stems"].items() if v["pass"]}
        old = stored.get(sd) or {}
        if old.get("stem") in passing:
            out[sd] = old
            continue
        times = sorted({float(x["start_s"]) for r in di_rows.values()
                        if str(pathlib.Path(r["path"]).parent) == str(pathlib.Path(sd))
                        for x in r["sections"] if x.get("own", True)})
        if not passing or not times:
            out[sd] = {"none": "no passing stem" if not passing else "no D-build section"}
            continue
        out[sd] = {"none": "no passing stem plays in a D-build section"}
        for f in sorted(passing, key=lambda f: (-stem_risk(passing[f]), f))[:tries]:
            act = activity(pathlib.Path(sd) / f, times)
            t = max(times, key=lambda t: (act[t], -t))
            if act[t] >= min_share:
                risk = stem_risk(passing[f])
                out[sd] = {"stem": f, "start_s": t, "share": round(act[t], 3),
                           "risk_db": risk if math.isfinite(risk) else None}
                break
    return out


def unheard_window(di, row, rs):
    """The window an unheard DI is queued on (the every-DI rule): a seeded D4-passed section, its own first."""
    import random as _r

    ok = [x["start_s"] for x in row["sections"] if rs["d4_sections"][x["section"]] == "pass"]
    own = [x["start_s"] for x in row["sections"] if x.get("own", True) and rs["d4_sections"][x["section"]] == "pass"]
    pick = own or ok
    return _r.Random(f"{D4_SAMPLE_SEED}:{di}").choice(pick) if pick else None


def update_registry(registry, queue, di_rows):
    """Add the queue's items to the registry (every item ever queued, so old exports still decode). A retired item
    stays retired, and every silent window is (re)marked retired."""
    for q in queue:
        old = registry.get(q["id"]) or {}
        registry[q["id"]] = dict(q, **({"retired": old["retired"]} if old.get("retired") else {}))
    for iid in silent_items(registry, di_rows):
        registry[iid]["retired"] = "a silent window: its answers are skipped"
    return registry


def sample_passed(di_rows, seed=D4_SAMPLE_SEED):
    """One D4-passed DI per band (pool and V_sep DIs with no D4-flagged section), seeded: queued for the ear to check
    D4's misses. A draw on a DI the measures exclude (D1-D3, or silent everywhere) would hear nothing for the band, so
    it is redrawn within the band from the rest (its own seeded stream; the other bands' draws are unchanged).
    -> {di: section start_s}."""
    import random as _r

    def own_pass(di):
        d4 = di_row_status(di_rows[di])["d4_sections"]
        return [x["start_s"] for x in di_rows[di]["sections"] if x.get("own", True) and d4[x["section"]] == "pass"]

    def measured_out(di):
        rs = di_row_status(di_rows[di])
        return di_verdict(rs["status"])[0] == "excluded" or all(
            rs["d4_sections"][x["section"]] == "silent" for x in di_rows[di]["sections"])

    by = {}
    for di, row in sorted(di_rows.items()):
        if not ({"training pool", "V_sep"} & set(row["datasets"])):
            continue
        d4 = di_row_status(row)["d4_sections"]
        own = [x for x in row["sections"] if x.get("own", True)]
        if own and all(d4[x["section"]] in ("pass", "silent") for x in own) and any(d4[x["section"]] == "pass" for x in own):
            by.setdefault(row["band"], []).append(di)
    rng = _r.Random(seed)
    out = {}
    for band in sorted(by):
        di = rng.choice(by[band])
        t = rng.choice(own_pass(di))
        if measured_out(di):
            rest = [d for d in by[band] if not measured_out(d)]
            if not rest:
                continue
            r2 = _r.Random(f"{seed}:{band}")
            di = r2.choice(rest)
            t = r2.choice(own_pass(di))
        out[di] = t
    return out


def cmd_lists(args):
    """The trusted lists and the ear queue (zero renders). Refuses when any `dis` or `stem-scan` shard is missing,
    incomplete or stale, when `targets` is incomplete or stale, or when a target lacks its crop row; every verdict is
    recomputed from the stored readings under the current thresholds."""
    from learn import pretrain_set as PS

    require_real(args)
    root = out_root(args)
    tgrec = _load(root / "t0" / "targets.json")
    if not tgrec:
        raise SystemExit("run `targets` first")
    probs = []
    if tgrec.get("thresholds") != thresholds():
        probs.append("targets.json was measured under other thresholds")
    if not tgrec.get("complete"):
        probs.append("targets.json is incomplete")
    dis, p1 = load_shards(root, "dis", "rows", lambda d: d.get("thresholds") == thresholds())
    floor = stem_floor(root)
    stems, p2 = load_shards(root, "stems", "sessions", lambda d: d.get("floor_db") == floor)
    probs += p1 + p2
    lt = label_table()
    tg = tgrec["parts"]
    crop_rows = {k[5:]: v for k, v in dis.items() if k.startswith("crop:")}
    di_rows = {k[3:]: v for k, v in dis.items() if k.startswith("di:")}
    no_crop = sorted(s for s in tg if s in lt and s not in crop_rows)
    if no_crop:
        probs.append(f"{len(no_crop)} targets lack their crop (measure DI) row: {no_crop[:5]}")
    if probs and not args.smoke:
        raise SystemExit("lists refuses: " + "; ".join(probs))
    for p in probs:
        print("smoke: ignoring:", p)
    if not args.ear_di and not args.smoke:
        raise SystemExit("lists needs --ear-di <the data-review-1 sitting-1 export>: without it the DIs sitting 1 "
                         "heard processed read as unheard")
    exports = export_records((args.ear or []) + (args.ear_di or []))
    prev = _load(root / "t0" / "verified.json")
    dropped = dropped_exports(prev, exports) if prev and bool(prev.get("smoke")) == bool(args.smoke) else []
    if dropped and not args.drop_ear:
        raise SystemExit("lists refuses: an earlier run read these answer exports, and this run would drop their "
                         f"answers: {dropped}. Pass every export each time (a later export of the same ear-page part "
                         "replaces an earlier one), or --drop-ear to drop them on purpose")
    for p in dropped:
        print(f"--drop-ear: dropping the answers in {p}")
    reg_path = root / "t0" / "ear-items.json"
    registry = _load(reg_path) or {}
    for iid in silent_items(registry, di_rows):
        registry[iid]["retired"] = "a silent window: its answers are skipped"
    quiet_ids, quiet_keys = quiet_windows(root)
    for iid in quiet_ids & set(registry):
        registry[iid]["retired"] = "a quiet window (the DI hardly plays here): its answers are skipped"
    ear = ear_answers(args.ear or [], args.ear_di or [], registry)
    if ear["superseded"]:
        print(f"{ear['superseded']} answers replaced by a later export of the same item")
    queue = []

    # the crops' measure DIs: D2-D3 measured; D4 and the ear (a negative wins; heard clean and D4-flagged: a conflict)
    crop_di, crop_heard, crop_meas = {}, {}, {}
    for slug, cr in crop_rows.items():
        st = crop_status(cr)
        heard = merge_ear([v for vs in ear["crop_di"].get(slug, {}).values() for v in vs]
                          + [v for _, _, v in ear["di_windows"].get(f"crop:{slug}", [])], "clean")
        resolved = merge_ear([v for _, _, v in ear["di_windows"].get(f"crop:{slug}", [])], "clean")
        crop_heard[slug] = merge_ear([v for vs in ear["crop_di"].get(slug, {}).values() for v in vs], "clean")
        crop_meas[slug] = st["D4"]
        inv = cr.get("inventory_di")                     # the same DI file heard on another window, or with its amp
        file_bad = bool(inv) and (any(merge_ear([v], "clean") is False for _, _, v in ear["di_windows"].get(inv, []))
                                  or merge_ear(ear["di_pairs"].get(inv, []), "amp") is False)
        file_heard = bool(inv) and (any(merge_ear([v], "clean") is True for _, _, v in ear["di_windows"].get(inv, []))
                                    or merge_ear(ear["di_pairs"].get(inv, []), "amp") is True)
        if "fail" in (st["D2"], st["D3"]):
            v, why = "excluded", [f"{m} fails" for m in ("D2", "D3") if st[m] == "fail"]
        elif heard is False:
            v, why = "excluded", ["heard processed or not a clean DI"]
        elif file_bad:
            v, why = "excluded", ["its DI file was heard processed (another window) or not a DI of an amp take"]
        elif st["D4"] == "fail" and resolved is not True:       # only a queue answer on the flagged window clears it
            conflict = heard is True
            v, why = "pending ear", ["conflict: heard clean, D4 flags it" if conflict else "D4 flags it (unheard)"]
        elif heard is not True and not file_heard:              # every DI is heard before it counts (user, 2026-10-24)
            v, why = "pending ear", ["unheard: every DI is heard before it counts"]
        else:
            v, why = "verified", []
        crop_di[slug] = {"verdict": v, "why": why, "status": st, "ear": heard, "d4": cr["d4"], "d2": cr["d2"]}
    agreement = d4_agreement({s: h for s, h in crop_heard.items()}, crop_meas)

    # targets: A1-A6 recomputed; the ear on the target (clean, amp); the measure DI's standing
    targets = {}
    for slug, r in tg.items():
        if "readings" not in r:
            targets[slug] = {"verdict": "excluded", "why": [r.get("error", "not measured")], "uses": r.get("uses")}
            continue
        st = target_status(r)
        ec, ea = ear_clean_of(slug, ear["target_clean"]), ear_amp_of(slug, ear["target_amp"])
        v, why = target_verdict(st, ec, ea, in_mix=r.get("in_mix", False))
        md = crop_di.get(slug)
        heard_bad = ec is False or ea is False or bool(md and md["verdict"] == "excluded" and any(
            w.startswith(("heard", "its DI file")) for w in md["why"]))
        if md and md["verdict"] == "pending ear" and v != "excluded":   # the measure DI waits for the ear too
            cr = crop_rows[slug]
            kind = {"conflict": "di_conflict", "unheard": "di_unheard"}.get(md["why"][0].split(":")[0], "di_flagged")
            queue.append(queue_item(kind, f"crop:{slug}", "di", cr["window_s"],
                                    CROP_S, {"di": cr["di_file"]}, md["why"][0], crest_db=cr["d4"]["crest_db"],
                                    bright_slope=cr["d4"]["bright_slope"]))
        if md and md["verdict"] == "excluded" and v != "excluded":
            v, why = "excluded", [f"measure DI: {', '.join(md['why'])}"]
        elif md and md["verdict"] == "pending ear" and v == "verified":
            v, why = "pending ear", [f"measure DI: {', '.join(md['why'])}"]
        targets[slug] = {"verdict": v, "why": why, "uses": r["uses"], "band": r["band"], "status": st,
                         "bleed_db": r["bleed_db"], "lag_ms": {h: r["readings"]["halves"][h]["lag_ms"] for h in HALVES},
                         "a3": r["readings"]["a3"], "a5": r["a5"], "heard_bad": heard_bad}
        if v == "pending ear":
            from learn import build_data_review as BDR

            crop = pathlib.Path(lt[slug]["crop"])
            for h in HALVES:
                if merge_ear(ear["target_clean"].get((slug, h), []), "clean") is None:
                    a, b = BDR.HALF_CLIPS[h]
                    queue.append(queue_item("target", slug, "target", a, b - a,
                                            {"di": str(crop / "di.wav"), "target": str(crop / "reference.wav")},
                                            "; ".join(why) or "not yet heard", half=h,
                                            question="The DI, then the target: is the target clean (no bleed, no "
                                                     "other guitar) and an amp recording?"))

    # pool, V_sep and other-guitar DIs: D1-D3 measured; D4 per section never decides alone; the ear decides
    sample = sample_passed(di_rows)
    dis_out, unusable, by_band = {}, set(), {}
    for di, row in sorted(di_rows.items()):
        rs = di_row_status(row)
        for x in row["sections"]:
            if (di, round(float(x["start_s"]), 1)) in quiet_keys:
                rs["d4_sections"][x["section"]] = "silent"       # a quiet window: the DI hardly plays here
        audible = [x for x in row["sections"] if rs["d4_sections"][x["section"]] != "silent"] or row["sections"]
        sampled = di in sample and (di, round(float(sample[di]), 1)) not in quiet_keys
        v, why = di_verdict(rs["status"])
        wins = windows_of(di, ear, crop_rows)
        pairs = merge_ear(ear["di_pairs"].get(di, []), "amp")
        if any(merge_ear([w[2]], "clean") is False for w in wins) or pairs is False:
            v, why = "excluded", ["heard processed, or not a DI of an amp take"]
        elif v == "pending ear":
            left = []
            for w in why:
                if w == "D1 to the ear" and pairs is True:
                    continue
                if w.startswith("DI-only") and any(merge_ear([x[2]], "clean") is True for x in wins):
                    continue
                left.append(w)
            v, why = ("pending ear", left) if left else ("verified", [])
        if v != "excluded" and row["sections"] and all(rs["d4_sections"][x["section"]] == "silent"
                                                       for x in row["sections"]):
            v, why = "excluded", ["silent in every section: nothing to hear, and no mix uses it"]
        heard_clean = any(merge_ear([w[2]], "clean") is True for w in wins)   # 'unsure' is not heard clean
        heard = heard_clean or pairs is True          # a window heard clean, or the pair heard as an amp take of it
        if v != "excluded" and sampled and not heard:
            v, why = "pending ear", why + ["sampled for the ear (D4 passed)"]
        secs = {}
        for x in row["sections"]:
            sid, t0 = x["section"], x["start_s"]
            e = section_ear(t0, wins)
            if v == "excluded" or rs["d2_sections"][sid] == "fail":
                secs[sid] = "excluded"
            elif rs["d4_sections"][sid] == "silent":
                secs[sid] = "silent"                              # the DI does not play here: no mix uses it
            elif rs["d4_sections"][sid] == "fail" and not (e is True and any(
                    covers(a, b, t0) and merge_ear([vv], "clean") for a, b, vv in ear["di_windows"].get(di, []))):
                secs[sid] = "pending ear"                         # flagged: only a queue answer on this section clears it
            elif v == "pending ear":
                secs[sid] = "pending ear"
            else:
                secs[sid] = "usable"
        if v == "verified" and any(secs[x["section"]] == "pending ear" and rs["d4_sections"][x["section"]] == "fail"
                                   for x in row["sections"]):
            # processing is a property of the DI (heard processed: excluded with all its sections), so the DI waits
            # while any window D4 flags is not yet heard clean
            v, why = "pending ear", ["D4 flags a window not yet heard clean"]
            secs = {k: ("pending ear" if s == "usable" else s) for k, s in secs.items()}
        if v == "verified" and not heard:             # every DI is heard before it counts (user, 2026-10-24)
            v, why = "pending ear", ["not yet heard (every DI is heard before it counts)"]
            secs = {k: ("pending ear" if s == "usable" else s) for k, s in secs.items()}
        unusable |= {sid for sid, s in secs.items() if s != "usable"}
        dis_out[di] = {"verdict": v, "why": why, "status": rs["status"], "d1": rs["d1"], "datasets": row["datasets"],
                       "band": row["band"], "sections": secs,
                       "own_sections": [x["section"] for x in row["sections"] if x.get("own", True)]}
        if v == "excluded":
            continue
        flagged = [x for x in row["sections"] if secs[x["section"]] == "pending ear"
                   and rs["d4_sections"][x["section"]] == "fail"]
        for x in flagged:
            queue.append(queue_item("di_flagged", di, "di", x["start_s"], CROP_S, {"di": row["path"]},
                                    "D4 flags this section (unheard)", crest_db=x["D4"]["crest_db"],
                                    bright_slope=x["D4"]["bright_slope"]))
        if "D1 to the ear" in why:
            x = busiest_audible(audible)
            amp = (x["D1"] or {}).get("amp_track")
            sess = pathlib.Path(row["path"]).parent
            queue.append(queue_item("di_amp", di, "di_amp", x["start_s"], CROP_S,
                                    {"di": row["path"], "amp": str(sess / amp) if amp else None},
                                    "D1 went to the ear (no readable lag or roll-off)",
                                    question="The DI, then its amp track: is the DI the clean DI of this amp take?"))
        if any(w.startswith("DI-only") for w in why) and not flagged:   # a flagged window heard clean clears it too
            x = busiest_audible(audible)
            queue.append(queue_item("di_only", di, "di", x["start_s"], CROP_S, {"di": row["path"]},
                                    "a DI-only part (no amp track to check it against)"))
        if not heard and not any(q["key"] == di for q in queue) and (sampled or "not yet heard" in why[0]):
            t = sample[di] if sampled else unheard_window(di, row, rs)     # nothing else of it is queued
            if t is not None:
                queue.append(queue_item("di_sample", di, "di", t, CROP_S, {"di": row["path"]},
                                        "a D4-passed DI, not yet heard"))
    for di, d in dis_out.items():
        if {"training pool", "V_sep"} & set(d["datasets"]):
            b = by_band.setdefault(d["band"], {"sections": 0, "usable": 0, "pending ear": 0, "excluded": 0, "silent": 0})
            for sid in d["own_sections"]:
                b["sections"] += 1
                b[d["sections"][sid]] += 1

    # the level prior's parts: A1-A4 and A6 not failed (a part waiting for the ear on A1 or A2 counts; it is a level
    # statistic, not a label), less any part the ear has rejected (the target, or its measure DI)
    passing = {s for s, r in targets.items() if r.get("status") and not r.get("heard_bad") and all(
        r["status"].get(m) in ("pass", "ear") for m in ("A1", "A2", "A3", "A4", "A6"))}
    crop_only = {s: float(tg[s].get("crop_start_s") or json.loads(
        (pathlib.Path(lt[s]["crop"]) / "record.json").read_text())["excerpt_start_s"])
        for s in passing if targets[s]["status"].get("A5") == "fail"}
    prior, counts = rederive_prior(PS.SECTIONS_MS, passing - set(crop_only), crop_only)
    old = PS.ratio_values()
    stored = (_load(root / "t0" / STEM_CHECK_FILE) or {}).get("sessions") or {}
    checks = pick_stem_checks(stems, di_rows, stored)
    _save(root / "t0" / STEM_CHECK_FILE, {"plan": PLAN, "smoke": bool(args.smoke), "sessions": checks,
                                         "rule": "per session, the passing stem nearest the floor, at its busiest "
                                                 "D-build section; the session's stems are used once it is heard clean"})
    stem_heard = {}
    for sd, c in checks.items():
        if "stem" not in c:
            continue
        key = f"{sd}|{c['stem']}"
        stem_heard[sd] = merge_ear(ear["stems"].get(key, []), "clean")
        if stem_heard[sd] is None:
            queue.append(queue_item("stem", key, "stem", c["start_s"], CROP_S, {"stem": str(pathlib.Path(sd) / c["stem"])},
                                    "the stem spot-check: the passing stem nearest the floor",
                                    question="Is an electric guitar audible in this track?"))
    # a session's stems are used once its spot-check is heard clean; a guitar heard holds all of them (the scan missed
    # one there), and unheard or 'unsure' waits
    verified_stems = {sd: sorted(f for f, v in r["stems"].items() if v["pass"]) for sd, r in stems.items()
                      if stem_heard.get(sd) is True}

    def uses(v, u):
        return sorted(s for s, r in targets.items() if r["verdict"] == v and u in (r.get("uses") or []))

    seen = set()
    queue = [q for q in queue if not (q["id"] in seen or seen.add(q["id"]))]
    quiet = silent_items({q["id"]: q for q in queue}, di_rows) | (quiet_ids & {q["id"] for q in queue})
    if quiet:
        print(f"left out of the ear queue: {len(quiet)} silent or quiet windows")
        queue = [q for q in queue if q["id"] not in quiet]
    update_registry(registry, queue, di_rows)
    counts_q = {}
    for q in queue:
        counts_q[q["kind"]] = counts_q.get(q["kind"], 0) + 1
    qrec = {"plan": PLAN, "page": EAR_PAGE, "smoke": bool(args.smoke), "counts": counts_q, "items": len(queue),
            "dis": len({q["key"] for q in queue if q["family"] != "target"}),
            "targets": len({q["key"] for q in queue if q["family"] == "target"}),
            "verdicts": {k: list(v) for k, v in EAR_VERDICTS.items()}, "queue": queue,
            "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(root / "t0" / "ear-queue.json", qrec)
    _save(reg_path, registry)
    rec = {"plan": PLAN, "smoke": bool(args.smoke), "thresholds": thresholds(),
           "ear_files": [str(p) for p in args.ear or []], "ear_di_files": [str(p) for p in args.ear_di or []],
           "ear_exports": exports, "ear_notes": ear["notes"], "targets": targets, "dis": dis_out, "measure_dis": crop_di, "unusable_sections": sorted(unusable),
           "stems": verified_stems, "stem_floor_db": floor,
           "stem_checks": {sd: {**c, "heard": stem_heard.get(sd)} for sd, c in checks.items()},
           "v_real": uses("verified", "stage F"), "v_real_pending": uses("pending ear", "stage F"),
           "kc2_verified": uses("verified", "knob ceiling 2"), "kc2_pending": uses("pending ear", "knob ceiling 2"),
           "k_dis": sorted(d for d, v in dis_out.items() if v["verdict"] == "verified" and "V_sep" in v["datasets"]
                           and v["band"] not in K_OUT_BANDS),
           "training_dis": sorted(d for d, v in dis_out.items() if v["verdict"] == "verified"
                                  and "training pool" in v["datasets"]),
           "d4_agreement_with_ear": agreement, "pool_sections_by_band": by_band,
           "level_prior": {"rederived": prior, "rederived_summary": prior_summary(prior), "old_summary": prior_summary(old),
                           "per_part": counts, "crop_only_a5": crop_only},
           "ear_queue": {"items": len(queue), "counts": counts_q}, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(root / "t0" / "verified.json", rec)
    for v in ("verified", "pending ear", "excluded"):
        print(f"targets {v}: {sum(1 for r in targets.values() if r['verdict'] == v)}; "
              f"DIs {v}: {sum(1 for r in dis_out.values() if r['verdict'] == v)}")
    print(f"V-real: {len(rec['v_real'])} verified, {len(rec['v_real_pending'])} pending the ear; knob ceiling 2: "
          f"{len(rec['kc2_verified'])} verified, {len(rec['kc2_pending'])} pending")
    print(f"K's DIs {len(rec['k_dis'])} ({REMOVED}); training DIs {len(rec['training_dis'])}")
    print(f"stems usable: {sum(len(v) for v in verified_stems.values())} in {len(verified_stems)} sessions "
          f"(floor {floor:.0f} dB; a session's stems once its spot-check is heard clean)")
    sh = list(stem_heard.values())
    print(f"stem spot-check: {len(sh)} sessions; heard clean {sh.count(True)}, a guitar heard {sh.count(False)} "
          f"(their stems held), waiting {sh.count(None)}; no check {sum(1 for c in checks.values() if 'none' in c)}")
    print(f"level prior: re-derived {rec['level_prior']['rederived_summary']}; old {rec['level_prior']['old_summary']}")
    a = agreement
    print(f"D4 against the ear (crops): {a['agree']}/{a['heard']} agree; processed missed {a['processed_missed']}; "
          f"heard clean but flagged (conflicts) {a['clean_flagged']}")
    print("pool and V_sep sections (usable / pending ear / excluded) per band: "
          + ", ".join(f"{b} {v['usable']}/{v['pending ear']}/{v['excluded']}" for b, v in sorted(by_band.items())))
    print(f"EAR QUEUE: {len(queue)} items ({qrec['dis']} DIs, {qrec['targets']} targets): {counts_q}")
    if ear["notes"]:
        print(f"NOTES ({len(ear['notes'])}; read them before T1: a note can qualify or replace a verdict):")
        for n in ear["notes"]:
            print(f"  {n['kind'] or n['page']} {n['key'] or n['id']} [{n['verdict'] or 'no verdict'}]: {n['note']}")


# --- commands: the re-reads (zero renders) -----------------------------------------------------------------------

def subset_stats(rows, keep):
    """CR.stats over [(band, value)] of the rows whose slug is kept. rows: [(slug, band, value)]."""
    from learn import confirm_run as CR

    sel = [(b, v) for s, b, v in rows if s in keep]
    if len({b for b, _ in sel}) < 2:
        return {"n": len(sel), "note": "too few bands"}
    return CR.stats(sel)


def cmd_reread(args):
    """The plan's re-reads on the verified panel (zero renders), each beside its stored headline: knob ceiling's
    K_S - S, K_S ceiling's extension, knob ceiling 2's (e) and time effects, amp choice; and the listening
    footnotes. Prints the dated notes for the results docs."""
    import math as _m

    from learn import every_control as EC
    from learn import knob_ceiling as K
    from learn import knob_ceiling2 as K2
    from learn import ks_extend as KS

    require_real(args)
    root = out_root(args)
    tr = _load(root / "t0" / "verified.json")
    if not tr:
        raise SystemExit("run `lists` first")
    keep = set(tr["kc2_verified"])                       # the panel: no measured fail (the plan's "12 parts") ...
    if not args.verified_only:
        keep |= set(tr["kc2_pending"])                  # ... the ear's confirmation pending beside
    cells = [json.loads(p.read_text()) for p in sorted((K.OUT / "cells").glob("*/*/result.json"))]
    out = {"panel": sorted(keep), "verified_only": bool(args.verified_only)}
    ks_vs_s = [(c["slug"], c["band"], K.cell_rows(c)[0]["KS_vs_S"]) for c in cells if "KS_vs_S" in K.cell_rows(c)[0]]
    out["knob ceiling K_S - S (cells)"] = {"all": subset_stats(ks_vs_s, {s for s, _, _ in ks_vs_s}),
                                          "verified": subset_stats(ks_vs_s, keep)}
    base, res = KS.base_figures(), KS.stored_results()
    sub = lambda d: {k: v for k, v in d.items() if k[0] in keep}                 # noqa: E731
    out["K_S ceiling (extension, at stop)"] = {"all": KS.summarise(base, res)["estimate_at_stop"]["all"],
                                               "verified": KS.summarise(sub(base), sub(res))["estimate_at_stop"]["all"]}
    s1 = [json.loads(p.read_text()) for p in sorted((K2.OUT / "stage1").glob("*/[AB].json"))]
    e = [(r["slug"], r["band"], r["gain_class"], _m.log(r["held"] / r["start_held"])) for r in s1]
    out["knob ceiling 2 (e)"] = {"all": K2._stats(K2._per_part([x for x in e])),
                                 "verified": K2._stats(K2._per_part([x for x in e if x[0] in keep]))}
    s2 = [(p.parent.name, json.loads(p.read_text())) for p in sorted((K2.OUT / "stage2").glob("*/[AB].json"))]
    t = [(r.get("slug") or slug, r["band"], r["gain_class"], _m.log(r["held"] / r["start_held"])) for slug, r in s2]
    out["knob ceiling 2 time effects (stage 2 - stage 1, judge)"] = {
        "all": K2._stats(K2._per_part(t)), "verified": K2._stats(K2._per_part([x for x in t if x[0] in keep])),
        "large_cells_on_failing_parts": sorted([(x[0], round(x[3], 3)) for x in t if x[0] not in keep and x[3] < -0.05])}
    ac = EC.amp_choice_rows(cells)
    out["amp choice (part-weighted mean; band-weighted beside)"] = {
        "all": subset_stats([(s, b, v) for s, b, _, v in ac], {s for s, *_ in ac}),
        "verified": subset_stats([(s, b, v) for s, b, _, v in ac], keep)}
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

    print(f"Dated notes ({date}; verified panel of {len(keep)} parts):")
    for k_, v in out.items():
        if isinstance(v, dict) and "verified" in v:
            print(f"- {k_}: all {f(v['all'])}; verified {f(v['verified'])}")
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
    ap.add_argument("--drop-ear", action="store_true",
                    help="lists: drop the answers of exports an earlier run read and this run leaves out")
    ap.add_argument("--verified-only", action="store_true", help="reread: only parts the ear has confirmed")
    args = ap.parse_args(argv)
    if (args.limit or args.only) and not args.smoke:
        raise SystemExit("--limit and --only are for smoke runs (with --smoke and --out)")
    {"negatives": cmd_negatives, "calibrate": cmd_calibrate, "targets": cmd_targets, "dis": cmd_dis,
     "inject-strict": cmd_inject_strict, "stem-scan": cmd_stem_scan, "lists": cmd_lists, "reread": cmd_reread}[args.cmd](args)


if __name__ == "__main__":
    main()
