"""The from-scratch search's tone split: the first price, by the score, of the measure step's clip, and where row (c)'s
loss is made (`docs/scratch-search-plan.md` section 11; ledger `preset-ladder` `phase_scratch_tone`, then
`phase_scratch_tone_split`). The search row `fs-tone` is held, not declared: nothing here searches.

Rows (b) and (c)'s stored, hashed answers on all 47 parts of the draw are re-scored through six dry guitars, each
setting primed alone and judged on the held half against the clean record, with the coded true DI as the judge's DI
every time (18 renders a part, `ARMS`):

| Dry guitar | What it is | Rendered through it |
|---|---|---|
| `true` | the coded true DI (`note_replay.di_section`), as rows (b) and (c) were scored | Cen (the control: its stored value and render sha256 exactly) |
| `true-noclip` | the raw section through the measure step with the +-15 dB clip removed in every bin, at -22.9 LUFS | Cen, answer (c), answer (b) |
| `avg` | stored: the true DI with the average balance (`note_replay` blur) | answer (c) |
| `true+planted` | the coded true DI with exactly the seeded +-3 dB a decade tilt | answer (c) |
| `true+tilt` | the coded true DI with avg+mild's truth-fitted tilt (clipped to +-8) | answer (c) |
| `avg+mild` | stored: the search's own dry guitar | Cen, answer (c) |

    $MAIN -m learn.scratch_tone fit                  # zero renders, before the declaration: its version and sha256
    $MAIN -m learn.scratch_tone split --shard 0/3    # and 1/3, 2/3: 846 renders in all
    $MAIN -m learn.scratch_tone split-read           # zero renders, once: P_c, P_b, the C numbers, phi, the codes

`fit` runs from any checkout whose `learn/scratch_search.py` and `phase_fs*` keys are main's; `split` and `split-read`
refuse unless this checkout runs main's `learn/scratch_search.py` and `learn/scratch_tone.py` and main's
`phase_scratch_tone*` keys (`on_main`), and main holds `phase_scratch_tone` with the fit's version and sha256 and the
user's go, `phase_scratch_both_outcome`, the draw's hash and both rows' answers' hashes.

The pure parts (the tilt form and its fit, the planted sign, the readings, `MC_TABLE`, `TN_TABLE` and their guards, the
shares, phi, the reach rule, the linear answer, the per-part numbers, the split's per-part body with a stub renderer,
every refusal) are tested in tests/test_scratch_tone.py on the light CI runner (no numpy); the audio parts and the fit's
numbers where numpy and the stored data exist. `song_bank.measure` and `direc_check.eq_to` are not changed.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import time

from learn import note_replay as NR
from learn import scratch_notes as SN
from learn import scratch_search as S

LEDGER_ID = S.LEDGER_ID                  # preset-ladder
PLAN = "docs/scratch-search-plan.md"
SECTION = 11
PHASE = "phase_scratch_tone"             # this declaration (the fit's version and sha256, the user's go)
PHASE_SPLIT = "phase_scratch_tone_split" # the audited outcome
KEY_PREFIX = "phase_scratch_tone"
HELD_KEYS = ("phase_scratch_tone_hook", "phase_scratch_tone_answers", "phase_scratch_tone_outcome")  # held: fs-tone
HELD_ROW = "fs-tone"
GATE = "phase_scratch_both_outcome"      # row (c)'s audited outcome on main
ROWS = ("fs-stem", "fs-both")            # rows (b) and (c), whose stored answers are re-scored
ROW_OF = {"b": "fs-stem", "c": "fs-both"}
PARTS = sum(S.COUNTS.values())           # 47: every part of the draw
REFUSAL_STOP = S.REFUSAL_STOP            # 3 refused of 47 stop the read
SMALL, BIG = S.SMALL, S.BIG              # 0.05, 0.10 (the user's rule)
CODED = "true"                           # the coded true DI: the judge's DI every time
NOCLIP = "true-noclip"
ARMS = (                                 # (dry guitar, settings rendered through it); "c", "b": rows (c), (b)'s answers
    (CODED, ("cen",)),
    (NOCLIP, ("cen", "c", "b")),
    ("avg", ("c",)),
    ("true+planted", ("c",)),
    ("true+tilt", ("c",)),
    ("avg+mild", ("cen", "c")))
DRIES = tuple(d for d, _ in ARMS)
BUILT = (NOCLIP, "true+tilt", "true+planted")    # built by `fit`, hashed in its file
STORED_DRY = ("avg", "avg+mild")                 # the replay's blur, checked against blur.json
RENDERS_PER_RENDER = 2                           # a priming render and the kept one (`fresh_render`)
RENDERS_PER_PART = RENDERS_PER_RENDER * sum(len(s) for _, s in ARMS)    # 18
PLANTED_DB = 3.0                         # the seeded tilt's size (`di_robustness.degrade`)
TILT_CAP = 8.0                           # fitted tilts are clipped to +-8 dB a decade
GRID_N, GRID_LO, GRID_HI = 81, 80.0, 8000.0      # the fit's grid, geometric
BAND = (80.0, 8000.0)                    # the in-band distances (weights 1/f, the weighted mean removed)
REACH = 12.0                             # the 9-band EQ's +-12 dB
CLIP_DB = 15.0                           # `direc_check.eq_to`'s clip (read only: the clipped share)
EQ_BAND_DECADES = math.log10(2)          # phi from the EQ answers: one band taken as one octave (the review's estimate)
FIT_VERSION = 1                          # a changed fit writes the next version; the declaration names it
C_NUMBERS = {"C_fix": NOCLIP, "C_avg": "avg", "C_planted": "true+planted", "C_tilt": "true+tilt",
             "C_blur": "avg+mild"}       # answer (c) through the dry guitar less answer (c) through the coded true DI
TONE_NUMBERS = ("C_tilt", "C_planted", "C_avg", "C_fix")     # "the tone costs" only from these
P_NUMBERS = ("P_c", "P_b")
NUMBERS = P_NUMBERS + tuple(C_NUMBERS)
GROUP_ANSWER = {"P_b": "b"}              # the linear-answer group of each number: by the answer it scores (else (c)'s)


# --- the tilt and its fit (pure; lists or numpy arrays) -------------------------------------------------------------------

def _log_clip(f):
    return max(-1.0, min(1.0, math.log10(max(float(f), 1.0)) - 3.0))


def tilt_gain_db(freqs, s):
    """(Pure.) The tilt form: gain in dB = s * clip(log10(f / 1 kHz), -1, +1) (0 at 1 kHz, +-s at 10 kHz and 100 Hz, flat
    outside). On a numpy array it is `di_robustness.degrade`'s formula exactly (at s = 3 times the sign, its tilt)."""
    if hasattr(freqs, "dtype"):
        import numpy as np

        return s * np.clip(np.log10(np.maximum(freqs, 1)) - 3.0, -1, 1)
    return [s * _log_clip(f) for f in freqs]


def grid_freqs(n=GRID_N, lo=GRID_LO, hi=GRID_HI):
    """(Pure.) The fit's grid: n points, geometric, lo to hi."""
    return [lo * (hi / lo) ** (i / (n - 1)) for i in range(n)]


def _centred(v):
    v = [float(x) for x in v]
    m = sum(v) / len(v)
    return [x - m for x in v]


def fit_slope(curve, grid):
    """(Pure.) The least-squares slope s (dB a decade) of the tilt form on `grid` against `curve`, both mean-removed:
    a curve that is a tilt of slope s plus a constant returns s."""
    b, c = _centred(tilt_gain_db(grid, 1.0)), _centred(curve)
    return sum(x * y for x, y in zip(b, c)) / sum(x * x for x in b)


def detilt(curve, grid, s):
    """(Pure.) The curve, mean-removed, less the tilt of slope s (mean-removed)."""
    b, c = _centred(tilt_gain_db(grid, 1.0)), _centred(curve)
    return [y - s * x for x, y in zip(b, c)]


def rms(v):
    v = [float(x) for x in v]
    return math.sqrt(sum(x * x for x in v) / len(v))


def capped(s, cap=TILT_CAP):
    return max(-cap, min(cap, s))


def planted_sign(pkey):
    """(Pure.) The seeded sign of the mild blur's tilt for a part: `note_replay.cmd_blur`'s draw, the first in
    `di_robustness.degrade("mild")`."""
    return random.Random(f"{NR.BLUR_SEED}|mild|{pkey}").choice((-1, 1))


def planted_slope(pkey):
    return PLANTED_DB * planted_sign(pkey)


# --- the readings and the codes (pure) -------------------------------------------------------------------------------------

def _iv_ok(iv):
    return bool(iv) and all(iv.get(k) is not None for k in ("mean", "lo90", "hi90"))


def readable(iv, small=SMALL):
    """(Pure.) False when the interval sits inside +-small ("not readable by the score"); None without an interval."""
    if not _iv_ok(iv):
        return None
    return not (iv["lo90"] >= -small and iv["hi90"] <= small)


def mc_reading(iv, small=SMALL):
    """(Pure.) One row's reading of its P: "level" (the interval inside +-small); "moves" (the interval clear of zero
    and the mean at small or beyond, either way); "undecided" otherwise (not failed). None without an interval."""
    if not _iv_ok(iv):
        return None
    m, lo, hi = iv["mean"], iv["lo90"], iv["hi90"]
    if lo >= -small and hi <= small:
        return "level"
    if (lo > 0 or hi < 0) and abs(m) >= small:
        return "moves"
    return "undecided"


MC_READINGS = ("level", "moves", "undecided")
MC_TABLE = (     # (code, row, reading, what it tells the user); one reading a row, P_c for (c), P_b for (b), on the pool
    ("MC-c-level", "c", "level",
     "row (c)'s stored number stands under the fix, as far as re-scoring can show (it is conservative)"),
    ("MC-c-moves", "c", "moves",
     "row (c) carries the fault. Its restated number comes from this split; a redo of its search would show at least "
     "this change"),
    ("MC-c-undecided", "c", "undecided", "the size and interval go to the user"),
    ("MC-b-level", "b", "level", "row (b)'s stored number stands under the fix; its search needs no redo"),
    ("MC-b-moves", "b", "moves",
     "row (b)'s stored answers are tied to the coded DI. The re-scored number is where a redo starts: a redo should "
     "match it up to search noise. Nothing is claimed above it, and the stored G is not a ceiling: the fix moves the DI "
     "further from the raw guitar that made the record, on some parts beyond the EQ's reach, so the task may be harder. "
     "An exact row (b) needs its search redone under the fixed DI: 12,351 + 940 renders, about 1 h 59 min at the "
     "measured rates"),
    ("MC-b-undecided", "b", "undecided", "the size and interval go to the user"))
MC_CODES = tuple(c for c, *_ in MC_TABLE)
MC_TOGETHER = (  # (row (c)'s reading or None for any, row (b)'s reading, the sentence): read together, the first that holds
    ("level", "level", "rows (b) and (c) stand; no redo for their sake; fixing the measure step is a forward-only "
                       "choice"),
    ("moves", "level", "restate row (c) and the share from the split; no search is redone"),
    (None, "moves", "the share on one yardstick is given from the split, and an exact one waits on row (b)'s redo"))


def row_code(row, iv):
    """(Pure.) MC_TABLE's code for one row from its own interval only (P_c for "c", P_b for "b"). -> {code, row,
    reading, tells, readable} or None without an interval."""
    if row not in ROW_OF:
        raise ValueError(row)
    r = mc_reading(iv)
    if r is None:
        return None
    hit = [t for t in MC_TABLE if t[1] == row and t[2] == r]
    if len(hit) != 1:
        raise SystemExit(f"MC_TABLE holds row {row} reading {r} {len(hit)} times")
    code, _, _, tells = hit[0]
    return {"code": code, "row": row, "reading": r, "tells": tells, "readable": readable(iv)}


def _reading_of(code):
    return code.rsplit("-", 1)[1] if code else None


def mc_together(code_c, code_b):
    """(Pure.) The joint sentence for the two rows' codes, or None (each code then goes to the user on its own line)."""
    rc, rb = _reading_of(code_c), _reading_of(code_b)
    for c, b, text in MC_TOGETHER:
        if (c is None or c == rc) and b == rb:
            return text
    return None


TN_TABLE = (     # (code, when, wording); on BKS+GOAT, descriptive: it licenses no run
    ("TN-reach", "C_tilt decided better: its interval below zero, its mean at -0.10 or beyond",
     "by the split, a static tone error of avg+mild's size is worth a heard size; C_planted says how much of it is our "
     "own tilt"),
    ("TN-short", "not the above, and one of the C numbers has its interval below zero",
     "{what} costs ({names}); not a heard size by the split"),
    ("TN-search", "no C number has its interval below zero",
     "not shown by the split that row (c)'s loss is carried by the dry guitar. With phi under 0.5 this is expected even "
     "if it is"))
TN_CODES = tuple(c for c, *_ in TN_TABLE)


def below_zero(iv):
    return _iv_ok(iv) and iv["hi90"] < 0


def tn_code(cs, big=BIG):
    """(Pure.) TN_TABLE's code from the five C numbers' intervals on BKS+GOAT (cs: {name: interval or None}; a missing
    interval is never below zero). TN-short's wording says "the tone costs" only when a tone number (C_tilt,
    C_planted, C_avg, C_fix) is below zero, else "the blur costs (smear, soft clip and bleed included)". Every stop is
    worded "not shown by the split". -> {code, wording, below_zero}."""
    if set(cs) != set(C_NUMBERS):
        raise SystemExit(f"tn_code needs the five C numbers, not {sorted(cs)}")
    below = [n for n in C_NUMBERS if below_zero(cs.get(n))]
    text = {c: w for c, _, w in TN_TABLE}
    t = cs.get("C_tilt")
    if below_zero(t) and t["mean"] <= -big:
        return {"code": "TN-reach", "wording": text["TN-reach"], "below_zero": below}
    if below:
        tone = [n for n in below if n in TONE_NUMBERS]
        what = "the tone" if tone else "the blur (smear, soft clip and bleed included)"
        return {"code": "TN-short", "wording": text["TN-short"].format(what=what, names=", ".join(below)),
                "tone": bool(tone), "below_zero": below}
    return {"code": "TN-search", "wording": text["TN-search"], "below_zero": below}


def table_guard():
    """Refuse unless MC_TABLE holds each row's three readings once, TN_TABLE its three codes in order, ARMS 18 renders
    a part, the key prefix is outside every guarded prefix, and 0 < SMALL < BIG."""
    from learn import note_transcribe as NT

    for row in ROW_OF:
        if sorted(t[2] for t in MC_TABLE if t[1] == row) != sorted(MC_READINGS):
            raise SystemExit(f"MC_TABLE does not hold row {row}'s three readings once each")
    if TN_CODES != ("TN-reach", "TN-short", "TN-search"):
        raise SystemExit("TN_TABLE's codes are not the three declared, in order")
    if RENDERS_PER_PART != 18:
        raise SystemExit(f"ARMS render {RENDERS_PER_PART} a part, not 18")
    pre = [p for ps in NT.KEY_PREFIXES.values() for p in ps]
    if KEY_PREFIX.startswith(tuple(pre)) or KEY_PREFIX.startswith("phase_fs"):
        raise SystemExit(f"{KEY_PREFIX} sits under a guarded prefix")
    if not 0 < SMALL < BIG:
        raise SystemExit("the thresholds are not 0 < SMALL < BIG")


# --- the numbers (pure) ----------------------------------------------------------------------------------------------------

def beyond_reach(ask_max, ask_min, reach=REACH):
    """(Pure.) The fix asks for more than the 9-band EQ can answer: the in-band ask (centred in band) above +reach or
    below -reach anywhere."""
    return ask_max > reach or ask_min < -reach


def linear_answer(settings):
    """(Pure.) The answer is a linear chain: the compressor and both drives off (`scratch_search.DRIVE_KEYS`)."""
    return not any(str(settings.get(k, "false")).lower() in ("true", "1") for k in S.DRIVE_KEYS)


def _ln(a, b):
    return math.log(a / b) if S.finite_pos(a) and S.finite_pos(b) else None


def own_terms(held, dry, setting):
    """(Pure.) A setting's G in a dry guitar's own terms: ln(the setting through `dry` / Cen through `dry`), or None.
    held: {dry: {setting: held-half distance}}."""
    h = held.get(dry) or {}
    return _ln(h.get(setting), h.get("cen"))


def shares(c_noclip, b_noclip, b_stored, c_stored):
    """(Pure.) Section 4b's ratios, from pooled rows ({mean, ...}): the share restated on one yardstick (row (c)'s G over
    row (b)'s G, both through `true-noclip`), the stored share beside, and the mixed figure (row (c) re-scored over row
    (b) stored), labelled mixed in its key."""
    return {"share_one_yardstick": SN.share_of(c_noclip, b_noclip),
            "share_stored": SN.share_of(c_stored, b_stored),
            "share_mixed_c_rescored_over_b_stored": SN.share_of(c_noclip, b_stored)}


def held_values(rec):
    """(Pure.) A split record's held-half distances by dry guitar, non-finite ones replaced by B3's declared rule
    (`scratch_search.nonfinite_rule`) inside each dry guitar: the worst finite among the settings rendered through it,
    never better than its Cen (a dry guitar without a Cen render takes the coded true DI's Cen, the control). A dry
    guitar whose own Cen is non-finite gives no numbers. -> ({dry: {setting: value}}, {dry: [replaced]})."""
    raw = rec["held"]
    out, rep = {}, {}
    cen0 = raw[CODED]["cen"]
    for dry, vals in raw.items():
        own = "cen" in vals
        if own and not S.finite_pos(vals["cen"]):
            rep[dry] = ["cen"]
            continue
        h = dict(vals) if own else {"cen": cen0, **vals}
        got, r = S.nonfinite_rule(h)
        if not own:
            got.pop("cen")
        out[dry] = got
        if r:
            rep[dry] = r
    return out, rep


def part_values(held, stored):
    """(Pure.) One part's numbers. held: `held_values`'s; stored: {"G_c", "G_b" (rows (c), (b)'s stored G),
    "c" (answer (c)'s stored held distance)}. P_c, P_b: G through `true-noclip` less the stored G; the C numbers:
    answer (c) through the dry guitar less answer (c) through the coded true DI (stored); beside: G of both rows
    through `true-noclip`, Cen's shift between the two DIs, Cen's shift through avg+mild, and row (c) in its own terms
    through avg+mild."""
    g_c, g_b = own_terms(held, NOCLIP, "c"), own_terms(held, NOCLIP, "b")
    out = {"G_c_noclip": g_c, "G_b_noclip": g_b,
           "P_c": None if g_c is None or stored.get("G_c") is None else g_c - stored["G_c"],
           "P_b": None if g_b is None or stored.get("G_b") is None else g_b - stored["G_b"]}
    for name, dry in C_NUMBERS.items():
        out[name] = _ln((held.get(dry) or {}).get("c"), stored.get("c"))
    cen0 = (held.get(CODED) or {}).get("cen")
    out["cen_shift_noclip"] = _ln((held.get(NOCLIP) or {}).get("cen"), cen0)
    out["cen_shift_avg_mild"] = _ln((held.get("avg+mild") or {}).get("cen"), cen0)
    out["c_own_terms_avg_mild"] = own_terms(held, "avg+mild", "c")
    return out


def phi_part(dresp, err):
    """(Pure.) phi by render for a part: the share of avg+mild's spectrum error that shows, inverted, in the long-term
    response of answer (c) less answer (b): -<dresp, err> / <err, err>, both mean-removed (1 for a response that is the
    error inverted, 0 for none). None for a flat error."""
    d, e = _centred(dresp), _centred(err)
    ee = sum(x * x for x in e)
    return None if ee == 0 else -sum(x * y for x, y in zip(d, e)) / ee


def eq_slope(settings, amp):
    """(Pure.) The part's amp's 9-band EQ slope in dB a band (the review's least-squares line over bands 1 to 9), or
    None. A setting holds every amp's EQ keys, so the amp is the part's own."""
    try:
        b = [float(settings[f"{amp}EQ/{amp}EQBand{i}"]) for i in range(1, 10)]
    except (KeyError, TypeError, ValueError):
        return None
    return sum((i - 5) * v for i, v in zip(range(1, 10), b)) / sum((i - 5) ** 2 for i in range(1, 10))


def phi_eq(answers_b, answers_c, slopes, amps):
    """(Pure.) phi from the stored EQ answers (the review's regression, octave bands assumed): the least-squares slope
    of answer (c)'s EQ slope less answer (b)'s (dB a band) on avg+mild's fitted tilt (dB a decade), over -log10(2).
    answers_b, answers_c: {pkey: settings}; slopes: {pkey: slope}; amps: {pkey: the part's amp}. -> {parts, slope,
    phi} (None under 3 parts)."""
    xs, ys = [], []
    for k, s in sorted(slopes.items()):
        b, c = eq_slope(answers_b.get(k) or {}, amps[k]), eq_slope(answers_c.get(k) or {}, amps[k])
        if s is not None and b is not None and c is not None:
            xs.append(float(s))
            ys.append(c - b)
    if len(xs) < 3:
        return {"parts": len(xs), "slope": None, "phi": None}
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else None
    return {"parts": len(xs), "slope": b, "phi": None if b is None else b / -EQ_BAND_DECADES}


def negated(iv):
    """(Pure.) -x's interval: the average balance's cost is -C_avg."""
    if not _iv_ok(iv):
        return None
    return {**iv, "mean": -iv["mean"], "lo90": -iv["hi90"], "hi90": -iv["lo90"]}


# --- the split's per-part body (pure but for the functions handed in) -------------------------------------------------------

class DryRefused(SystemExit):
    """A dry guitar's audio is not the hashed one: nothing is rendered."""


def control_verdict(value, sha, stored):
    """(Pure.) The Cen control through the coded true DI: its value and render sha256 equal both rows' stored ones
    exactly. stored: {"b": (value, sha), "c": (value, sha)}."""
    ok = all(value == v and sha == h for v, h in stored.values())
    return {"ok": ok, "value": value, "render_sha256": sha,
            "stored": {r: {"value": v, "render_sha256": h} for r, (v, h) in stored.items()}}


def split_part(pkey, dries, want_sha, sha_of, settings, score, stored_cen):
    """One part of the split. dries: {dry: audio}; want_sha: {dry: the hashed sha256}; sha_of(audio) -> sha256;
    settings: {"cen", "c", "b": (select, settings)}; score(dry, select, settings) -> (distance, render sha256, spectrum
    on the grid), each one primed render and one kept; stored_cen: `control_verdict`'s stored. Every dry guitar's
    sha256 is checked before the part's first render (DryRefused otherwise); the Cen control first: a miss refuses
    the part (2 renders). -> the record (no settings values in it)."""
    shas = {}
    for dry in DRIES:
        got = sha_of(dries[dry])
        if got != want_sha.get(dry):
            raise DryRefused(f"{pkey}: the {dry} dry guitar is not the hashed one ({got[:12]}, not "
                             f"{str(want_sha.get(dry))[:12]}): nothing rendered")
        shas[dry] = got
    held, rsha, spectra, renders = {}, {}, {}, 0
    v, h, _ = score(CODED, *settings["cen"])
    renders += RENDERS_PER_RENDER
    ctl = control_verdict(v, h, stored_cen)
    base = {"plan": PLAN, "part": pkey, "ledger": f"{LEDGER_ID} {PHASE}", "dry_sha256": shas, "control": ctl}
    if not ctl["ok"]:
        return {**base, "refused": {"cen_control": ctl}, "renders": renders}
    held[CODED], rsha[CODED] = {"cen": v}, {"cen": h}
    for dry, names in ARMS:
        for nm in names:
            if dry == CODED and nm == "cen":
                continue
            v, h, sp = score(dry, *settings[nm])
            renders += RENDERS_PER_RENDER
            held.setdefault(dry, {})[nm] = v
            rsha.setdefault(dry, {})[nm] = h
            if dry == NOCLIP and nm in ("c", "b"):
                spectra[nm] = sp
    return {**base, "held": held, "render_sha256": rsha, "spectra_noclip": spectra, "renders": renders}


# --- paths, the ledger, refusals ---------------------------------------------------------------------------------------------

def tone_dir():
    return S.fs_dir() / "tone"


def fit_path(version=FIT_VERSION):
    return tone_dir() / f"fit-v{version}.json"


def dry_path(name, pk, version=FIT_VERSION):
    """A built dry guitar: PF/fs/tone/dry/v<version>/<name>/<part>.npy (a changed fit never overwrites one)."""
    if name not in BUILT:
        raise ValueError(name)
    return tone_dir() / "dry" / f"v{version}" / name / f"{pk}.npy"


def split_path(pk):
    return tone_dir() / "split" / f"{pk}.json"


def rows_path():
    return tone_dir() / "rows.json"


def report_path():
    return tone_dir() / "report.json"


def tone_keys(entry):
    """(Pure.) The `phase_scratch_tone*` keys of a `preset-ladder` entry."""
    return {k: v for k, v in (entry or {}).items() if k.startswith(KEY_PREFIX)}


CODE_FILES = ("learn/scratch_search.py", "learn/scratch_tone.py")


def on_main():
    """main's `preset-ladder` entry (origin/main after a fetch), and whether this checkout runs main's split: its
    learn/scratch_search.py and learn/scratch_tone.py and its `phase_scratch_tone*` keys equal main's (as
    `scratch_search.on_main`). -> (main's entry or None, refusal or None)."""
    import subprocess

    from learn import pipeline_fix as P

    def git(*a):
        return subprocess.run(["git", "-C", str(P.REPO), *a], capture_output=True, text=True)
    git("fetch", "-q", "origin", "main")
    led = git("show", "origin/main:docs/dev-test-ledger.json")
    if led.returncode:
        return None, f"main's ledger is not readable: {led.stderr.strip()}"
    m = NR.main_entry(led.stdout)
    for f in CODE_FILES:
        if git("diff", "--quiet", "origin/main", "--", f).returncode:
            return m, f"this checkout's {f} differs from main's: run from merged code"
    a, b = tone_keys(NR.ledger_entry()), tone_keys(m)
    if a != b:
        diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
        return m, f"this checkout's {', '.join(diff)} differ from main's: pull main (run from merged code)"
    return m, None


def declaration_refusal(main, fit_sha):
    """(Pure.) Why the split may not render or read, or None: main's entry must hold `phase_scratch_tone` naming this
    fit's version and sha256 and the user's go, and `phase_scratch_both_outcome`."""
    rec = (main or {}).get(PHASE)
    if not isinstance(rec, dict):
        return f"main's {LEDGER_ID} entry has no {PHASE}: merge the declaration first"
    fit = rec.get("fit") or {}
    if fit.get("version") != FIT_VERSION or fit.get("sha256") != fit_sha:
        return (f"main's {PHASE} names fit v{fit.get('version')} {str(fit.get('sha256'))[:12]}, not this fit "
                f"v{FIT_VERSION} {str(fit_sha)[:12]}")
    if not (rec.get("user_go") or {}).get("date"):
        return f"main's {PHASE} records no user's go"
    if GATE not in (main or {}):
        return f"main's {LEDGER_ID} entry has no {GATE}"
    return None


def require_split():
    """Refuse unless this checkout runs main's split and main holds the declaration with this fit and the user's go.
    -> (main's entry, the fit)."""
    table_guard()
    m, why = on_main()
    if why:
        raise SystemExit(why)
    p = fit_path()
    if not p.exists():
        raise SystemExit(f"no fit v{FIT_VERSION} (run `fit` first)")
    why = declaration_refusal(m, S.file_sha(p))
    if why:
        raise SystemExit(why)
    return m, json.loads(p.read_text())


def both_answers():
    """Rows (b) and (c)'s answers, each refused unless its sha256 is main's (`scratch_search.require_hash`)."""
    return {r: S.require_hash(S.phase_answers(ROW_OF[r]), S.answers_path(ROW_OF[r])) for r in ROW_OF}


def require_blur(draw):
    rec = json.loads((NR.replay_dir() / "blur.json").read_text())
    if rec["draw_sha256"] != draw["replay_draw_sha256"]:
        raise SystemExit("blur.json was made from another replay draw")
    return rec


# --- the audio parts (numpy) -------------------------------------------------------------------------------------------------

def _bins():
    import numpy as np

    from learn import di_robustness as DR

    return np.fft.rfftfreq(DR.N_FFT, 1 / DR.SR)


def spectrum(x):
    from learn import di_robustness as DR

    import numpy as np

    return DR.smoothed_spectrum(np.asarray(x, np.float64))


def on_grid(spec_db):
    """A smoothed spectrum (dB, N_FFT bins) on the fit's grid, mean-removed."""
    import numpy as np

    c = np.interp(np.array(grid_freqs()), _bins(), np.asarray(spec_db, np.float64))
    return c - c.mean()


def band_distance(spec_a, spec_b):
    """RMS (dB) of spec_a less spec_b over the bins from 80 Hz to 8 kHz, weights 1/f, the weighted mean removed."""
    import numpy as np

    f = _bins()
    m = (f >= BAND[0]) & (f <= BAND[1])
    w = 1 / f[m]
    w /= w.sum()
    d = (np.asarray(spec_a) - np.asarray(spec_b))[m]
    d = d - (d * w).sum()
    return float(np.sqrt((w * d * d).sum()))


def apply_tilt(x32, s):
    """The tilt form at slope s (dB a decade) applied with `di_robustness.apply_gain_db`, then back to the input's RMS,
    as float32; s = 0 returns the input object untouched."""
    if s == 0:
        return x32
    import numpy as np

    from learn import di_robustness as DR

    x = np.asarray(x32, np.float64)
    y = DR.apply_gain_db(x, tilt_gain_db(_bins(), s))
    return np.asarray(y * (DR.rms(x) / DR.rms(y)), np.float32)


def measure_gain(raw):
    """`song_bank.measure`'s asked gain on SPEC_N bins: avg - (own - own.mean()) (unclipped)."""
    import numpy as np

    from learn import confirm_run as CR
    from learn import di_robustness as DR

    avg = np.load(CR.AVERAGE)
    own = DR.smoothed_spectrum(np.asarray(raw, np.float64))
    return avg - (own - own.mean())


def no_clip_measure(raw):
    """`true-noclip`: `song_bank.measure` with the clip removed in every bin: its gain interpolated and applied as
    `direc_check.eq_to` does, without `np.clip`, then `direc_check.to_lufs` (-22.9 LUFS). On an input whose gain never
    reaches +-15 dB it equals `song_bank.measure`. (A new function: `measure` and `eq_to` are unchanged.)"""
    import numpy as np

    from learn.direc import SPEC_N
    from learn.direc_check import SR, to_lufs

    x = np.asarray(raw).astype(np.float64)
    g = measure_gain(x)
    n = len(x)
    gg = np.interp(np.fft.rfftfreq(n, 1 / SR), np.fft.rfftfreq(SPEC_N, 1 / SR), g)
    return to_lufs(np.fft.irfft(np.fft.rfft(x) * 10 ** (gg / 20), n))


def side_effects(raw, coded, noclip):
    """The fix's side effects for a part (zero renders): the in-band ask's largest boost and cut (centred in band), its
    uncentred in-band mean, the largest boost above 8 kHz and below 80 Hz (same centring), the clipped share in band,
    the rise in energy above 8 kHz and in peak of `true-noclip` against the coded DI, and the reach rule."""
    import numpy as np

    from learn.direc import SPEC_N
    from learn.direc_check import SR

    g = measure_gain(raw)
    f = np.fft.rfftfreq(SPEC_N, 1 / SR)
    m = (f >= BAND[0]) & (f <= BAND[1])
    gc = g - g[m].mean()

    def hf(x):
        x = np.asarray(x, np.float64)
        e = np.abs(np.fft.rfft(x)) ** 2
        return e[np.fft.rfftfreq(len(x), 1 / SR) > BAND[1]].sum()
    out = {"ask_in_band_max": float(gc[m].max()), "ask_in_band_min": float(gc[m].min()),
           "ask_in_band_mean_uncentred": float(g[m].mean()), "ask_above_8k_max": float(gc[f > BAND[1]].max()),
           "ask_below_80_max": float(gc[f < BAND[0]].max()),
           "clipped_share_in_band": float((np.abs(g[m]) > CLIP_DB).mean()),
           "hf_rise_db": float(10 * np.log10(hf(noclip) / hf(coded))),
           "peak_rise_db": float(20 * np.log10(np.abs(np.asarray(noclip, np.float64)).max()
                                               / np.abs(np.asarray(coded, np.float64)).max()))}
    out["beyond_reach"] = beyond_reach(out["ask_in_band_max"], out["ask_in_band_min"])
    return out


def level_spread(x):
    """The planning probe's level spread: 50-ms frame levels within 40 dB of the loudest, p95 - p50 and p50 - p10 (dB),
    and the crest factor (dB)."""
    import numpy as np

    from learn import di_robustness as DR

    x = np.asarray(x, np.float64)
    win = int(0.05 * DR.SR)
    n = len(x) // win
    e = 10 * np.log10((x[:n * win].reshape(n, win) ** 2).mean(1) + 1e-20)
    e = e[e > e.max() - 40]
    return {"up_db": float(np.percentile(e, 95) - np.percentile(e, 50)),
            "down_db": float(np.percentile(e, 50) - np.percentile(e, 10)),
            "crest_db": float(20 * np.log10(np.abs(x).max() / np.sqrt(np.mean(x ** 2))))}


def snr_db(a, b):
    """b against a after the best scalar gain (dB)."""
    import numpy as np

    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    g = (a * b).sum() / (b * b).sum()
    return float(10 * np.log10((a * a).sum() / ((a - g * b) ** 2).sum()))


def _save_dry(path, y32, n):
    import numpy as np

    y32 = np.asarray(y32, np.float32)
    if len(y32) != n or not np.isfinite(y32).all():
        raise SystemExit(f"{path.name}: a built dry guitar not finite or not the section's length")
    S.never_overwrite(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, y32)
    return S.file_sha(path)


def _aggregate(parts, keys):
    """The fit's figures pooled over `keys`: means and maxima, and the RMS over parts and grid before and after the
    tilt."""
    if not keys:
        return None

    def stat(get):
        v = [get(parts[k]) for k in keys]
        return {"mean": sum(v) / len(v), "max": max(v), "min": min(v)}
    out = {"parts": len(keys),
           "err_rms_over_parts_and_grid": math.sqrt(sum(parts[k]["err_rms"] ** 2 for k in keys) / len(keys)),
           "err_rms_after_tilt_over_parts_and_grid": math.sqrt(sum(parts[k]["err_rms_after_tilt"] ** 2
                                                                    for k in keys) / len(keys)),
           "slopes_inside_cap": sum(abs(parts[k]["slope_fit"]) <= TILT_CAP for k in keys),
           "planted_sign_matches_mild": sum(parts[k]["planted_sign_matches_mild"] for k in keys),
           "planted_sign_matches_fit": sum((parts[k]["slope_fit"] > 0) == (parts[k]["planted_sign"] > 0) for k in keys),
           "beyond_reach": sum(parts[k]["side_effects"]["beyond_reach"] for k in keys)}
    for name, get in (("dist_raw", lambda r: r["dist_from_average"]["raw"]),
                      ("dist_true", lambda r: r["dist_from_average"][CODED]),
                      ("dist_true_noclip", lambda r: r["dist_from_average"][NOCLIP]),
                      ("clip_residual", lambda r: r["clip_residual"]),
                      ("avg_vs_true_noclip", lambda r: r["avg_vs"][NOCLIP]),
                      ("avg_vs_true", lambda r: r["avg_vs"][CODED]),
                      ("fixed_avg_vs_avg", lambda r: r["avg_vs"]["fixed_avg"]),
                      ("fixed_avg_vs_true_noclip", lambda r: r["fixed_avg_vs_true_noclip"]),
                      ("clipped_share_in_band", lambda r: r["side_effects"]["clipped_share_in_band"]),
                      ("ask_in_band_mean_uncentred", lambda r: r["side_effects"]["ask_in_band_mean_uncentred"]),
                      ("ask_in_band_max", lambda r: r["side_effects"]["ask_in_band_max"]),
                      ("ask_in_band_min", lambda r: r["side_effects"]["ask_in_band_min"]),
                      ("ask_above_8k_max", lambda r: r["side_effects"]["ask_above_8k_max"]),
                      ("ask_below_80_max", lambda r: r["side_effects"]["ask_below_80_max"]),
                      ("hf_rise_db", lambda r: r["side_effects"]["hf_rise_db"]),
                      ("peak_rise_db", lambda r: r["side_effects"]["peak_rise_db"]),
                      ("abs_slope_fit", lambda r: abs(r["slope_fit"])),
                      ("snr_avg_mild_db", lambda r: r["snr_db"]["avg+mild"]),
                      ("spread_up_true", lambda r: r["level_spread"][CODED]["up_db"]),
                      ("spread_up_avg_mild", lambda r: r["level_spread"]["avg+mild"]["up_db"])):
        out[name] = stat(get)
    return out


def cmd_fit(_args):
    """The fit (zero renders, CPU only), once a version, before the declaration: per part of the draw the raw section,
    the coded true DI, `true-noclip`, `true+tilt` and `true+planted` (the built three saved under
    PF/fs/tone/dry/v<version>/ with their sha256, refused if not finite or not the section's length), avg+mild's error
    curve against the coded true DI on the grid, its fitted slope and the capped one, the error's RMS before and after
    the tilt, the stored mild file's fitted slope (the planted sign's check), the clip residual, the fix's side effects,
    each DI's distance from the average, the stored avg against `true-noclip`, the coded DI and the avg a fixed
    pipeline would build (`average_balance` of `true-noclip` on the same others, each measured without the clip), the
    level spread and the SNR. It reads no score file. -> PF/fs/tone/fit-v<version>.json; its version and sha256 go
    into the declaration."""
    table_guard()
    draw = S.require_draw()
    S.never_overwrite(fit_path())
    import hashlib

    import numpy as np

    from learn import confirm_run as CR
    from learn import di_robustness as DR
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    rd = NR.require_draw()
    sd = NR.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    blur = require_blur(draw)
    by_sec = {}
    for p in rd["parts"]:
        by_sec.setdefault(p["section"], sd.units[(p["set"], p["unit"], p["amp"])]["prt"])
    avg_target = np.load(CR.AVERAGE)
    orig, memo = DR.smoothed_spectrum, {}

    def cached(x):                                 # the same function, its value memoised by the audio's bytes
        key = hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()
        if key not in memo:
            memo[key] = orig(x)
        return memo[key]
    secs = {}

    def raw_of(s):
        prt = by_sec[s]
        return np.asarray(PS.section_audio(prt["di_path"], prt["start_s"]), np.float64)

    def noclip_of(s):                              # every section's clip-free DI as a dry guitar's float32, kept for
        if s not in secs:                          # the fixed pipeline's avg (as `note_replay.cmd_blur` reads them)
            secs[s] = np.asarray(np.asarray(no_clip_measure(raw_of(s)), np.float32), np.float64)
        return secs[s]
    grid = grid_freqs()
    rby = {p["pkey"]: p for p in rd["parts"]}
    parts, t0 = {}, time.time()
    DR.smoothed_spectrum = cached
    try:
        for n, p in enumerate(sorted(draw["parts"], key=lambda q: q["pkey"])):
            k = p["pkey"]
            prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
            raw = raw_of(p["section"])
            di32 = NR.di_section(prt)
            coded = np.asarray(di32, np.float64)
            nc32 = np.asarray(noclip_of(p["section"]), np.float32)
            dry = {d: NR.load_dry(d, rby[k], di32, blur) for d in STORED_DRY}
            mild = NR.load_dry("mild", rby[k], di32, blur)
            sp = {"raw": spectrum(raw), CODED: spectrum(coded), NOCLIP: spectrum(nc32),
                  "avg": spectrum(dry["avg"]), "avg+mild": spectrum(dry["avg+mild"]), "mild": spectrum(mild)}
            err = on_grid(sp["avg+mild"] - sp[CODED])
            s_fit = fit_slope(err, grid)
            s_mild = fit_slope(on_grid(sp["mild"] - sp[CODED]), grid)
            sign = planted_sign(k)
            built = {NOCLIP: nc32, "true+tilt": apply_tilt(di32, capped(s_fit)),
                     "true+planted": apply_tilt(di32, planted_slope(k))}
            files = {d: _save_dry(dry_path(d, k), y, len(di32)) for d, y in built.items()}
            shas = {CODED: S.npy_sha(di32), **{d: S.npy_sha(y) for d, y in built.items()},
                    **{d: S.npy_sha(dry[d]) for d in STORED_DRY}}
            for d in STORED_DRY:
                if shas[d] != blur["parts"][k]["sha256"][d]:
                    raise SystemExit(f"{k}: the stored {d} is not blur.json's")
            if any(files[d] != shas[d] for d in BUILT):
                raise SystemExit(f"{k}: a built dry guitar's file is not its audio's .npy form")
            oth = blur["parts"][k]["others"]
            fixed_avg = DR.average_balance(noclip_of(p["section"]),
                                           {src: [noclip_of(x) for x in xs] for src, xs in oth.items()})
            sp_fixed = spectrum(fixed_avg)
            parts[k] = {
                "set": p["set"], "cls": p["cls"], "sha256": shas, "planted_sign": sign, "slope_fit": s_fit,
                "slope_used": capped(s_fit), "slope_planted": planted_slope(k), "slope_mild": s_mild,
                "planted_sign_matches_mild": (s_mild > 0) == (sign > 0),
                "err_curve": [float(v) for v in err], "err_rms": rms(err),
                "err_rms_after_tilt": rms(detilt(err, grid, s_fit)),
                "err_rms_after_capped_tilt": rms(detilt(err, grid, capped(s_fit))),
                "clip_residual": band_distance(sp[CODED], sp[NOCLIP]),
                "side_effects": side_effects(raw, coded, nc32),
                "dist_from_average": {q: band_distance(sp[q], avg_target) for q in ("raw", CODED, NOCLIP)},
                "avg_vs": {NOCLIP: band_distance(sp["avg"], sp[NOCLIP]), CODED: band_distance(sp["avg"], sp[CODED]),
                           "fixed_avg": band_distance(sp_fixed, sp["avg"])},
                "fixed_avg_vs_true_noclip": band_distance(sp_fixed, sp[NOCLIP]),
                "level_spread": {CODED: level_spread(coded), "avg+mild": level_spread(dry["avg+mild"])},
                "snr_db": {"avg+mild": snr_db(coded, dry["avg+mild"]), "avg": snr_db(coded, dry["avg"])}}
            if n % 10 == 0:
                print(f"fit {n + 1}/{len(draw['parts'])}: {(time.time() - t0) / (n + 1):.1f} s each", flush=True)
    finally:
        DR.smoothed_spectrum = orig
    keys = sorted(parts)
    groups = {"bks_goat": [k for k in keys if parts[k]["set"] in SN.DECIDING],
              "goat": [k for k in keys if parts[k]["set"] == "goat"],
              "goat_clean": [k for k in keys if parts[k]["set"] == "goat" and parts[k]["cls"] == "clean"],
              "bks": [k for k in keys if parts[k]["set"] == "bks"],
              "panel": [k for k in keys if parts[k]["set"] == "panel"], "all": keys}
    out = {"plan": PLAN, "section": SECTION, "ledger": f"{LEDGER_ID} {PHASE}", "version": FIT_VERSION,
           "draw_sha256": S.file_sha(S.draw_path()), "blur_sha256": S.file_sha(NR.replay_dir() / "blur.json"),
           "grid": grid, "tilt_cap": TILT_CAP, "reach": REACH, "renders": 0, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
           "seconds": time.time() - t0, "summary": {g: _aggregate(parts, ks) for g, ks in groups.items()},
           "parts": parts}
    P.save(fit_path(), out)
    a, g = out["summary"]["bks_goat"], out["summary"]["goat"]
    print(f"FIT v{FIT_VERSION}: {len(parts)} parts, {time.time() - t0:.0f} s; error RMS GOAT "
          f"{g['err_rms_over_parts_and_grid']:.2f} -> {g['err_rms_after_tilt_over_parts_and_grid']:.2f}, the 40 "
          f"{a['err_rms_over_parts_and_grid']:.2f} -> {a['err_rms_after_tilt_over_parts_and_grid']:.2f}; beyond reach "
          f"{out['summary']['all']['beyond_reach']} of {len(parts)}; sha256 {S.file_sha(fit_path())} (into the "
          f"declaration as {PHASE})")


# --- the split (renders) -------------------------------------------------------------------------------------------------------

def score_dry(p, select, settings, dry32, judge_di32, sd, new_renderer, clean=None):
    """One setting through one dry guitar, primed alone (`audibility_measure.fresh_render`), judged on the held half
    against the clean record with `judge_di32` as the judge's DI (`note_replay.half_distance`, as `score_row_part`).
    -> (distance, render sha256, the render's spectrum on the grid)."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    if clean is None:
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        clean = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
    di = np.asarray(judge_di32, np.float64)[trim[0]:trim[1]]
    x = LO.tdict(settings)
    y = np.asarray(AM.fresh_render(new_renderer, dry32, select, x, x), np.float64)[trim[0]:trim[1]]
    if not np.isfinite(y).all():
        return math.inf, AM.audio_sha(np.nan_to_num(y)), None
    v = NR.half_distance(clean, y, di, p["lag"], p["held"])
    mono = y.mean(axis=1) if y.ndim == 2 else y      # a stereo render folded as the judge folds it (aligned._signal)
    return v, AM.audio_sha(y), [float(q) for q in on_grid(spectrum(mono))]


def stored_cen(k):
    """Both rows' stored Cen held value and render sha256 for a part (the control's reference)."""
    out = {}
    for r, row in ROW_OF.items():
        sc = json.loads(S.score_path(row, k).read_text())
        out[r] = (sc["held"]["cen"], sc["render_sha256"]["cen"])
    return out


def cmd_split(args):
    """One shard of the split (renders): per part (sorted by key, every n-th) the disk guard; the six dry guitars, each
    checked against the fit's sha256 (the stored two also against blur.json) before the part's first render; Cen
    through the coded true DI first (the control: value and render sha256 exactly both rows' stored); then ARMS'
    settings, each primed alone, the judge's DI the coded true DI. -> PF/fs/tone/split/<part>.json, written once."""
    m, fit = require_split()
    draw = S.require_draw()
    ans = both_answers()
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    import numpy as np

    NR.no_separation_beside()
    sd = NR.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    if fit["draw_sha256"] != S.file_sha(S.draw_path()):
        raise SystemExit("the fit was made from another draw")
    blur = require_blur(draw)
    rby = {p["pkey"]: p for p in NR.require_draw()["parts"]}
    k_, n_ = args.shard
    mine = [p for j, p in enumerate(sorted(draw["parts"], key=lambda p: p["pkey"])) if j % n_ == k_]
    LO._wait_cap()
    total, t0 = 0, time.time()
    for p in mine:
        k = p["pkey"]
        out = split_path(k)
        if out.exists():
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        di32 = NR.di_section(prt)
        dries = {CODED: di32, **{d: np.load(dry_path(d, k)).astype(np.float32) for d in BUILT},
                 **{d: NR.load_dry(d, rby[k], di32, blur) for d in STORED_DRY}}
        clean = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        sets = {"cen": (p["cen"]["select"], p["cen"]["settings"]),
                **{r: (ans[r]["parts"][k]["select"], ans[r]["parts"][k]["answer"]) for r in ROW_OF}}

        def score(dry, select, settings):
            return score_dry(p, select, settings, dries[dry], di32, sd, CB.new_renderer, clean=clean)
        rec = split_part(k, dries, fit["parts"][k]["sha256"], S.npy_sha, sets, score, stored_cen(k))
        rec.update(fit={"version": FIT_VERSION, "sha256": m[PHASE]["fit"]["sha256"]},
                   answers_sha256={r: S.file_sha(S.answers_path(ROW_OF[r])) for r in ROW_OF},
                   time=time.strftime("%Y-%m-%d %H:%M:%S"))
        S.never_overwrite(out)
        P.save(out, rec)
        total += rec["renders"]
        print(f"{k[-60:]}: {'REFUSED (Cen control)' if 'refused' in rec else 'ok'}; {total} renders, "
              f"{time.time() - t0:.0f} s", flush=True)
    print(f"TONE SPLIT DONE {k_}/{n_}: {total} renders in {time.time() - t0:.0f} s")


def _row(sd, draw, values, keys=None):
    return SN.set_rows(sd, draw, values, keys)


def _dp(row):
    return (row or {}).get("deciding_pool")


def _bg(row, sub="all"):
    return ((row or {}).get("bks_goat") or {}).get(sub)


def cmd_split_read(_args):
    """The split's read (zero renders), once: the stored G of both rows (`scratch_search.read_row_parts` on their
    hashed answers); every split file checked against this fit and these answers; the refusal stop (3 of 47); per part
    `part_values` and phi by render; every number by set, class, the linear-answer group and the reach groups; the
    shares; the average balance's cost (-C_avg) on its own line; P_c and P_b against the clip residual; phi from the EQ
    answers; the rows saved before any code; then the pool refusal, `row_code` for each row on the pool, `mc_together`,
    and `tn_code` on BKS+GOAT. -> PF/fs/tone/rows.json, report.json."""
    m, fit = require_split()
    S.never_overwrite(report_path())
    S.never_overwrite(rows_path())
    draw = S.require_draw()
    ans = both_answers()
    from learn import pipeline_fix as P

    sd = NR.Stored()
    rby = {p["pkey"]: p for p in NR.require_draw()["parts"]}
    per = {r: S.read_row_parts(draw, ans[r], S.file_sha(S.answers_path(ROW_OF[r])),
                               lambda k, row=ROW_OF[r]: S.score_path(row, k), sd, rby)[0] for r in ROW_OF}
    fit_sha = m[PHASE]["fit"]["sha256"]
    recs, refused, replaced, renders = {}, {}, {}, 0
    for p in draw["parts"]:
        k = p["pkey"]
        sp = split_path(k)
        if not sp.exists():
            raise SystemExit(f"{k}: not split")
        r = json.loads(sp.read_text())
        if (r.get("fit") or {}).get("sha256") != fit_sha:
            raise SystemExit(f"{k}: split through another fit")
        if r.get("answers_sha256") != {q: S.file_sha(S.answers_path(ROW_OF[q])) for q in ROW_OF}:
            raise SystemExit(f"{k}: split from other answers")
        renders += r["renders"]
        if "refused" in r:
            refused[k] = r["refused"]
            continue
        if any(per[q].get(k) is None for q in ROW_OF):
            refused[k] = {"stored": "a row has no stored numbers for this part"}
            continue
        recs[k] = r
    out = {"plan": PLAN, "section": SECTION, "ledger": f"{LEDGER_ID} {PHASE}", "fit": m[PHASE]["fit"],
           "renders": renders, "refused": refused, "stopped": S.stopped(refused, REFUSAL_STOP),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    if out["stopped"]:
        out["stop_reason"] = f"{len(refused)} of {PARTS} refused (the stop is {REFUSAL_STOP})"
        P.save(report_path(), dict(out, rows=None, codes="stopped"))
        print(f"TONE SPLIT: STOPPED ({out['stop_reason']})")
        return
    vals, phi_r = {n: {} for n in NUMBERS}, {}
    beside = {q: {} for q in ("G_c_noclip", "G_b_noclip", "cen_shift_noclip", "cen_shift_avg_mild",
                              "c_own_terms_avg_mild")}
    linear = {"c": set(), "b": set()}
    for k, r in recs.items():
        held, rep = held_values(r)
        if rep:
            replaced[k] = rep
        sc_c = json.loads(S.score_path(ROW_OF["c"], k).read_text())
        stored_c = S.nonfinite_rule(sc_c["held"])[0]["answer"]
        pv = part_values(held, {"G_c": per["c"][k]["G"], "G_b": per["b"][k]["G"], "c": stored_c})
        for n in NUMBERS:
            if pv[n] is not None:
                vals[n][k] = pv[n]
        for q in beside:
            if pv[q] is not None:
                beside[q][k] = pv[q]
        sp = r.get("spectra_noclip") or {}
        if sp.get("c") is not None and sp.get("b") is not None:
            phi_r[k] = phi_part([a - b for a, b in zip(sp["c"], sp["b"])], fit["parts"][k]["err_curve"])
        for q in ROW_OF:
            if linear_answer(ans[q]["parts"][k]["answer"]):
                linear[q].add(k)
    fp = fit["parts"]
    reach = {"beyond": {k for k in recs if fp[k]["side_effects"]["beyond_reach"]},
             "within": {k for k in recs if not fp[k]["side_effects"]["beyond_reach"]}}
    rows = {}
    for n in NUMBERS:
        lin = linear[GROUP_ANSWER.get(n, "c")]
        rows[n] = {"all": _row(sd, draw, vals[n]), "linear": _row(sd, draw, vals[n], lin),
                   "beyond_reach": _row(sd, draw, vals[n], reach["beyond"]),
                   "within_reach": _row(sd, draw, vals[n], reach["within"])}
    rows["beside"] = {q: _row(sd, draw, v) for q, v in beside.items()}
    rows["beside"]["phi_render"] = _row(sd, draw, {k: v for k, v in phi_r.items() if v is not None})
    rows["beside"]["phi_render_linear"] = _row(sd, draw, {k: v for k, v in phi_r.items() if v is not None},
                                               linear["c"])
    gc = {k: per["c"][k]["G"] for k in recs}
    gb = {k: per["b"][k]["G"] for k in recs}
    stored_rows = {"G_c": _row(sd, draw, gc), "G_b": _row(sd, draw, gb)}
    rows["stored"] = stored_rows
    nc_rows = {"c": rows["beside"]["G_c_noclip"], "b": rows["beside"]["G_b_noclip"]}
    rows["shares"] = {"pool": shares(_dp(nc_rows["c"]), _dp(nc_rows["b"]), _dp(stored_rows["G_b"]),
                                     _dp(stored_rows["G_c"])),
                      "bks_goat": shares(_bg(nc_rows["c"]), _bg(nc_rows["b"]), _bg(stored_rows["G_b"]),
                                         _bg(stored_rows["G_c"]))}
    rows["average_balance_cost"] = {"pool": negated(_dp(rows["C_avg"]["all"])),
                                    "bks_goat": negated(_bg(rows["C_avg"]["all"]))}
    clip = {k: fp[k]["clip_residual"] for k in recs}
    rows["by_clip_residual"] = {n: SN.by_figure(vals[n], clip) for n in P_NUMBERS}
    rows["side_effects_by_reach"] = {g: dict({f: (sum(fp[k]["side_effects"][f] for k in ks) / len(ks) if ks else None)
                                              for f in ("hf_rise_db", "peak_rise_db")}, parts=len(ks))
                                     for g, ks in reach.items()}
    slopes = {k: fp[k]["slope_fit"] for k in recs}
    ab = {k: ans["b"]["parts"][k]["answer"] for k in recs}
    ac = {k: ans["c"]["parts"][k]["answer"] for k in recs}
    cls_of = {p["pkey"]: (p["set"], p["cls"]) for p in draw["parts"]}
    phi_groups = {"goat_clean": lambda k: cls_of[k] == ("goat", "clean"),
                  "clean": lambda k: cls_of[k][1] == "clean" and cls_of[k][0] in SN.DECIDING,
                  "crunch": lambda k: cls_of[k][1] == "crunch" and cls_of[k][0] in SN.DECIDING,
                  "bks_goat": lambda k: cls_of[k][0] in SN.DECIDING, "pool": lambda k: True}
    amps = {p["pkey"]: p["amp"] for p in draw["parts"]}
    rows["phi_eq"] = {g: phi_eq(ab, ac, {k: v for k, v in slopes.items() if f(k)}, amps)
                      for g, f in phi_groups.items()}
    rows["phi_render_by_group"] = {g: (lambda v: {"parts": len(v), "mean": sum(v) / len(v) if v else None})(
        [phi_r[k] for k in phi_r if phi_r[k] is not None and f(k)]) for g, f in phi_groups.items()}
    rows["groups"] = {"linear_c": sorted(linear["c"]), "linear_b": sorted(linear["b"]),
                      "beyond_reach": sorted(reach["beyond"]), "within_reach": sorted(reach["within"])}
    out.update(nonfinite_replaced=replaced, parts={k: {n: vals[n].get(k) for n in NUMBERS} for k in recs})
    P.save(rows_path(), dict(out, rows=rows))               # the rows are saved before any code is read
    why = S.pool_refusal({"G": rows["P_c"]["all"], "I": rows["P_b"]["all"]})
    codes = {}
    if why:
        codes["mc"] = {"stopped": f"(G is P_c, I is P_b) {why}"}
    else:
        cc, cb = row_code("c", _dp(rows["P_c"]["all"])), row_code("b", _dp(rows["P_b"]["all"]))
        codes["mc"] = {"c": cc, "b": cb, "together": mc_together((cc or {}).get("code"), (cb or {}).get("code"))}
    codes["tn"] = tn_code({n: _bg(rows[n]["all"]) for n in C_NUMBERS})
    P.save(report_path(), dict(out, rows=rows, codes=codes))
    for n in NUMBERS:
        a, b = _dp(rows[n]["all"]) or {}, _bg(rows[n]["all"]) or {}
        print(f"{n}: pool {a.get('mean')} [{a.get('lo90')}, {a.get('hi90')}]; BKS+GOAT {b.get('mean')} "
              f"[{b.get('lo90')}, {b.get('hi90')}]")
    mc = codes["mc"]
    print(f"MC: {mc.get('stopped') or (mc['c'] or {}).get('code')}, {(mc.get('b') or {}).get('code')}; "
          f"{mc.get('together')}")
    print(f"TN {codes['tn']['code']}: {codes['tn']['wording']}")
    print(f"the average balance's cost (-C_avg) on BKS+GOAT: {rows['average_balance_cost']['bks_goat']}")


COMMANDS = {"fit": cmd_fit, "split": cmd_split, "split-read": cmd_split_read}


def main(argv=None):
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    for p_ in (str(root), str(root / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--shard", type=S._shard, default=(0, 1))
    args = ap.parse_args(argv)
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
