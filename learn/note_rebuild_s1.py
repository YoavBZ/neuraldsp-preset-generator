"""Stage 1 of the note rebuild, the true-notes test (`docs/note-rebuild-plan.md` section 11; ledger `note-rebuild`
`phase_nr_1`): on the replay's drawn GOAT parts that carry true notes, three dry guitars re-synthesised from GOAT's
true notes (`nr-plain`, `nr-level`, and the diagnostic `nr-oracle`) stand in for the replay's blurred DI, and the
replay's own pick and score read them against Cen and a blind pick on the GOAT-alone row.

    .venv/bin/python -m learn.note_rebuild_s1 subset   # the carrying subset (zero renders), its sha256 -> phase_nr_1_subset
    .venv/bin/python -m learn.note_rebuild_s1 build    # the dry guitars and their figures (CPU, zero renders)
    .venv/bin/python -m learn.note_rebuild_s1 gate     # prints the gate's reading from the replay's report
    .venv/bin/python -m learn.note_rebuild_s1 clips    # the ear check's clips on development items (48 renders)
    .venv/bin/python -m learn.note_rebuild_s1 render --shard k/3     # after the gate and the ear check (phase_nr_1_ear)
    .venv/bin/python -m learn.note_rebuild_s1 pick     # picks.json, its sha256 -> phase_nr_1_picks
    .venv/bin/python -m learn.note_rebuild_s1 score    # the rows, then N1_TABLE's code (once)

`subset` and `build` read no held-half value and render nothing; they may run before the replay's gate. `clips`,
`render`, `pick` and `score` refuse unless the gate reads go (`gate_refusal`, from the replay's own report and main's
ledger), and every command refuses unless this checkout runs main's code and main's ledger holds the phases it needs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import random
import time

from learn import note_rebuild as NR

LEDGER_ID = NR.LEDGER_ID
PHASE_1 = "phase_nr_1"                  # the declaration
PHASE_SUBSET = "phase_nr_1_subset"      # subset.json's sha256: before `build` and any render
PHASE_EAR = "phase_nr_1_ear"            # the user's ear check of the clips: {"verdict": "ok" | "fault", ...}
PHASE_BOTH_GO = "phase_nr_1_both_go"    # the user's go after a Both-row note (only when the replay's outcome has one)
PHASE_PICKS = "phase_nr_1_picks"        # picks.json's sha256: before `score` loads a held-half value
REPLAY_LEDGER = "preset-ladder"
GO_CODES = ("R-alone", "R-dry-only")    # the replay's continue codes; every other code stops stage 1
CLIP_SEED = 20261211                    # the ear check's development items
CLIP_ITEMS = 4
CLIP_AMP = "ac20"
CLIP_LUFS = -23.0                       # every clip at this integrated loudness (matched for A/B)
TERTILES = 3
# The carrying subset, hashed at declaration (2026-11-20, before the replay's `pick` or `score`): the replay's draw file
# and the sorted part keys `carrying_subset` gives on stage P's true-notes.json. `subset` refuses any other.
DECLARED_SUBSET = {"draw_sha256": "c0f834ada8d1d42b337be02a5f10812a3888353e6691a943500bf4a4b344f470",
                   "true_notes_sha256": "8b24b9c10332e298c188d38eaadd56dcc3b07227db250e752544f8b1db196506",
                   "parts": 60, "keys_sha256": "6570fa70ba80f06119c7de08168b98caad732a68fe694650dec26d690387dac9"}
BESIDE_F0 = "without_alignment_f0"      # every row read beside without the parts whose GOAT alignment F is 0.0
BESIDE_READER = "without_reader_fail"   # ... and without the parts whose item fails its own MIDI reader check
BESIDE_PRECHECK = "without_precheck_fail"   # ... and without the parts where a deciding arm fails a pre-check
BESIDE_PEAK = "without_peak_flag"       # ... and without the parts where a deciding arm's peak is flagged
PEAK_CONFOUND = ("A declared confound: the rebuilt guitars' attacks are sharper than the players' DIs (crest factor "
                 "6.1 to 10.1 dB higher on the flagged parts, measured on the stage-1 build), and the attack sets how hard the amp is driven. On N1-fail "
                 "or N1-between the read and its audit compare each arm's full row with its without_peak_flag row; a "
                 "row that reads differently without the flagged parts is said so before any route decision.")
CODE_FILES = ("learn/note_rebuild.py", "learn/note_rebuild_s1.py")


def out_dir():
    return NR.OUT / "stage1"


def clips_dir():
    return NR.HOME / "listening" / "note-rebuild-ear"


def subset_path():
    return out_dir() / "subset.json"


def build_path():
    return out_dir() / "build.json"


def dry_path(arm, pkey):
    return out_dir() / "di" / arm / f"{pkey.replace('/', '__')}.npy"


def dist_path(arm, pkey):
    return out_dir() / "dist" / arm / f"{pkey.replace('/', '__')}.json"


def picks_path():
    return out_dir() / "picks.json"


def report_path():
    return out_dir() / "report.json"


def rows_path():
    return out_dir() / "report-rows.json"


# --- pure pieces --------------------------------------------------------------------------------------------------------

def carrying_subset(parts, units):
    """(Pure.) The replay's drawn GOAT parts that carry true notes. parts: the draw's; units: true-notes.json's
    {unit|amp: record}. -> (carrying [{pkey, unit, amp, item, window_s}], left out [{pkey, why}])."""
    keep, out = [], []
    for p in sorted((p for p in parts if p["set"] == "goat"), key=lambda p: p["pkey"]):
        r = units.get(f"{p['unit']}|{p['amp']}")
        if r is None:
            out.append({"pkey": p["pkey"], "why": "not in true-notes.json"})
        elif not r.get("carries"):
            out.append({"pkey": p["pkey"], "why": r.get("why", "does not carry")})
        else:
            keep.append({"pkey": p["pkey"], "unit": p["unit"], "amp": p["amp"], "item": r["item"],
                         "window_s": r["window_s"]})
    return keep, out


R_OUTCOME_CODES = ("R-dry", "R-stem", "R-alone", "R-dry-only", "R-undecided", "singles-triggered", "incomplete")


def recorded_codes(rec):
    """(Pure.) The replay outcome codes named in main's `phase_replay_outcome` (a dict's "code", or the codes a string
    names as whole words). -> set."""
    import re

    if isinstance(rec, dict):
        rec = rec.get("code") or ""
    if not isinstance(rec, str):
        return set()
    return {c for c in R_OUTCOME_CODES if re.search(rf"(?<![\w-]){re.escape(c)}(?![\w-])", rec)}


def deciding_outcome(report, singles):
    """(Pure.) The replay's deciding outcome: report.json's, or, when it reads singles-triggered, report-singles.json's
    (None until it exists). -> (outcome or None, which: "main" | "singles")."""
    out = (report or {}).get("outcome") or {}
    if out.get("code") == "singles-triggered":
        return ((singles or {}).get("outcome"), "singles") if singles else (None, "singles")
    return out, "main"


def gate_refusal(report, replay_main, nr_main, singles=None):
    """(Pure.) Why stage 1 may not pick or read, or None. report: the replay's report.json (or None); singles: its
    report-singles.json (or None); replay_main: main's `preset-ladder` entry; nr_main: main's `note-rebuild` entry.
    The gate reads go only when:
    - report.json was read from the picks hashed on main (`phase_replay_picks`);
    - when report.json reads singles-triggered (the blurred DI failed or read undecided), report-singles.json exists and
      was read from the single-blur picks hashed on main (`phase_replay_picks_singles`), and its outcome decides;
    - main's `phase_replay_outcome` records exactly the deciding outcome's code (an audit correction closes the gate);
    - that code is R-alone or R-dry-only (the dry guitar passed, through the combined blur or a single one, and the
      stem alone passed);
    - when the deciding outcome carries a Both-row note, the user's go is recorded on main (`phase_nr_1_both_go`)."""
    if report is None:
        return "the replay has not been read (no report.json)"
    rec = (replay_main or {}).get("phase_replay_picks")
    if not isinstance(rec, dict) or rec.get("sha256") != report.get("picks_sha256"):
        return "the replay's report was not read from the picks hashed on main"
    out, which = deciding_outcome(report, singles)
    if which == "singles":
        if out is None:
            return "the replay's single-blur rows are not read yet (no report-singles.json)"
        rec2 = (replay_main or {}).get("phase_replay_picks_singles")
        if not isinstance(rec2, dict) or rec2.get("sha256") != singles.get("picks_sha256"):
            return "the replay's single-blur report was not read from the picks hashed on main"
    code = out.get("code")
    if "phase_replay_outcome" not in (replay_main or {}):
        return "the replay's outcome is not audited and recorded on main (phase_replay_outcome)"
    if recorded_codes(replay_main["phase_replay_outcome"]) != {code}:
        return f"main's phase_replay_outcome does not record exactly the report's code {code}"
    if code not in GO_CODES:
        return f"the replay reads {code}: stage 1 does not run"
    if out.get("both_notes") and PHASE_BOTH_GO not in (nr_main or {}):
        return "the replay's outcome carries a Both-row note: the user is asked before stage 1 (phase_nr_1_both_go)"
    failed = failed_both_rows(report, singles)
    if failed and PHASE_BOTH_GO not in (nr_main or {}):
        return (f"the replay's Both row {', '.join(failed)} fails: the user is asked before stage 1 (plan section 5; "
                "phase_nr_1_both_go)")
    return None


def failed_both_rows(report, singles=None):
    """(Pure.) The replay's Both rows (the stem and a blurred dry guitar together: both-alone, both-full and the
    single-blur avg-both-*, mild-both-*) that read "fails", in the main report and the single-blur report. Plan
    section 5: if a Both row fails, the user is asked before stage 1, whichever row the outcome's cell rests on."""
    out = []
    for rep_ in (report, singles):
        for name, r in sorted(((rep_ or {}).get("readings") or {}).items()):
            if "both" in name and (r or {}).get("reading") == "fails":
                out.append(name)
    return out


def comparison_dry(outcome):
    """(Pure.) The replay dry guitar stage 1's Blurred comparison row is read from: the one the deciding outcome rests
    on (`via`): the combined blur, or the passing single blur (avg first when both pass, mild beside). -> (main,
    [beside])."""
    via = (outcome or {}).get("via") or "avg+mild"
    names = [v.strip() for v in via.split(",")]
    if names == ["avg+mild"]:
        return "avg+mild", []
    names = [n for n in ("avg", "mild") if n in names]
    if not names:
        raise ValueError(f"not a dry guitar: {via}")
    return names[0], names[1:]


def subset_refusal(draw_sha, keys, declared=DECLARED_SUBSET, true_notes_sha=None):
    """(Pure.) Why the subset is not the one declared, or None: the replay's draw file, stage P's true-notes.json file
    and the sorted part keys must hash to the declaration's."""
    if draw_sha != declared["draw_sha256"]:
        return "the replay's draw is not the one the subset was declared on"
    if true_notes_sha is not None and true_notes_sha != declared["true_notes_sha256"]:
        return "true-notes.json is not the one the subset was declared on"
    if len(keys) != declared["parts"] or NR.content_sha(sorted(keys)) != declared["keys_sha256"]:
        return "the carrying parts are not the declared 60"
    return None


def without_f0(sub_parts):
    """(Pure.) The subset's part keys whose GOAT alignment F is not 0.0 (the beside row)."""
    return [k["pkey"] for k in sub_parts if k.get("alignment_f") != 0.0]


def ear_refusal(nr_main):
    """(Pure.) Why the ear check does not allow stage 1's renders, or None."""
    rec = (nr_main or {}).get(PHASE_EAR)
    if not isinstance(rec, dict) or "verdict" not in rec:
        return "the ear check of the clips is not recorded on main (phase_nr_1_ear)"
    if rec["verdict"] != "ok":
        return f"the ear check reads {rec['verdict']}: fix the fault under a declared revision first"
    return None


def ref_on_section(ref, n, trim, delay):
    """(Pure.) The clean record moved onto the DI section's timeline: the record is trimmed (it starts `trim` samples
    into the section) and lags the DI by `delay` samples (the plugin's latency plus the part's judge lag). -> n
    samples, zeros where the record has none."""
    import numpy as np

    out = np.zeros(n)
    shift = trim - delay                               # section index t holds record index t - shift
    lo, hi = max(0, shift), min(n, shift + len(ref))
    if hi > lo:
        out[lo:hi] = ref[lo - shift:hi - shift]
    return out


def tertile_edges(values, k=TERTILES):
    """(Pure.) The k-1 edges splitting the sorted finite values into k groups of near-equal size."""
    v = sorted(x for x in values if x is not None and math.isfinite(x))
    if len(v) < k:
        return []
    return [v[(len(v) * j) // k] for j in range(1, k)]


def group_of(x, edges):
    """(Pure.) The tertile index of x (0 lowest) by `edges`; None for a missing value."""
    if x is None or not math.isfinite(x):
        return None
    return sum(x >= e for e in edges)


def blind_setting(pkey, menu_n, seed=CLIP_SEED + 1):
    """(Pure.) Stage 3's blind menu setting for a part: a seeded menu position other than Cen (position 0)."""
    return 1 + random.Random(f"{seed}|blind|{pkey}").randrange(menu_n - 1)


def n3_card_eligible(pick, blind):
    """(Pure.) A stage-3 card is drawn only where the pick differs from Cen (position 0) and from the blind setting: an
    equal pair is a forced tie, which the sign test leaves out anyway; such parts are counted and reported."""
    return pick is not None and pick != 0 and pick != blind


# --- the automated pre-checks (the PR #528 review's ear-gate ruling; thresholds fixed here) ----------------------------

PRECHECK = {
    "peak_over_true_db": 6.0,           # report only (2026-11-20 amendment): a peak this far over the true DI's
    "tuning_cents": 5.0,                # each arm's global tuning against the true DI's (circular, in cents)
    "gap_frame_s": 0.020,               # the hiss floor: 20-ms frames where both the true DI and the arm are ...
    "gap_below_db": 30.0,               # ... at least 30 dB under their own loudest frame
    "gap_min_frames": 5,
    "gap_floor_over_true_db": 6.0,      # the arm's energy above 3 kHz in those gaps at most 6 dB over the true DI's
    "hf_hz": 3000.0,
    "burst_frame_s": 0.005,             # crunch renders: 5-ms frames of energy above 3 kHz ...
    "burst_rise_db": 12.0,              # ... a burst 12 dB over the running median of 100 ms ...
    "burst_median_s": 0.100,
    "burst_onset_s": 0.030,             # ... away from any onset by more than 30 ms
    "burst_rate_over_true": 0.5,        # the arm's burst rate (per second) at most 0.5 over the true DI's render's
    "level_spread_db": 3.0,             # nr-plain: plain onset groups each played alone, 50-ms levels, 90th less 10th
                                        # percentile at most 3 dB (the riff library's even chords; articulated groups
                                        # carry their declared gains and are left out)
    "level_min_groups": 5,
}


def mono(x):
    """(Pure.) A render folded to mono: the plugin's output is (samples, channels); a 1-D signal is returned as it is."""
    import numpy as np

    x = np.asarray(x, np.float64)
    return x.mean(axis=1) if x.ndim == 2 else x


def _frames_db(x, n, hp=None, rate=NR.SR):
    import numpy as np
    import scipy.signal as ss

    x = mono(x)
    if hp is not None:
        x = ss.sosfilt(ss.butter(4, hp, "hp", fs=rate, output="sos"), x)
    k = len(x) // n
    return 10 * np.log10(np.mean(np.asarray(x[:k * n]).reshape(k, n) ** 2, axis=1) + 1e-20)


def tuning_diff(a, b):
    """(Pure.) a - b in cents, folded into [-50, 50)."""
    return (a - b + 50.0) % 100.0 - 50.0


def gap_floor_diff(true_di, dry, rate=NR.SR, c=PRECHECK):
    """(Pure.) The hiss floor: the arm's mean energy above `hf_hz` in the frames where both signals are quiet (each at
    least `gap_below_db` under its own loudest frame), less the true DI's there, in dB; None with fewer than
    `gap_min_frames` such frames (a note ringing in one signal is not hiss)."""
    import numpy as np

    n = int(c["gap_frame_s"] * rate)
    k = min(len(true_di), len(dry))
    lv, ld = _frames_db(true_di[:k], n), _frames_db(dry[:k], n)
    gaps = (lv <= lv.max() - c["gap_below_db"]) & (ld <= ld.max() - c["gap_below_db"])
    if gaps.sum() < c["gap_min_frames"]:
        return None
    ht, hd = _frames_db(true_di[:k], n, c["hf_hz"]), _frames_db(dry[:k], n, c["hf_hz"])
    m = min(len(ht), len(gaps))
    g = gaps[:m]
    mean_db = lambda v: 10 * np.log10(np.mean(10 ** (v[:m][g] / 10)) + 1e-20)   # noqa: E731
    return float(mean_db(hd) - mean_db(ht))


def level_spread(notes, bank, length, rate=NR.SR):
    """The evenness of nr-plain's struck levels: each onset group with no articulation gain and its onset inside the
    window, synthesised alone (`note_rebuild.synthesise`), its RMS over LEVEL_SPAN_S from the onset; the 90th less the
    10th percentile in dB. None with fewer than `level_min_groups` such groups. (At declaration, on 27 development
    windows: 0.2 to 1.8 dB; with every group, articulated ones included, 6 to 10 dB, which is the declared gains.)"""
    import numpy as np

    db = []
    for g in NR.onset_groups(notes):
        gn = [notes[k] for k in g]
        if gn[0]["on"] < 0 or any(NR.note_gain_db(n) for n in gn):
            continue
        y, _ = NR.synthesise(gn, length, bank, 0.0, None, rate)
        a = int(round(gn[0]["on"] * rate))
        db.append(20 * math.log10(NR.span_rms(y, a, a + int(NR.LEVEL_SPAN_S * rate)) + 1e-12))
    if len(db) < PRECHECK["level_min_groups"]:
        return None
    return float(np.percentile(db, 90) - np.percentile(db, 10))


def burst_rate(render, onsets_s, rate=NR.SR, c=PRECHECK):
    """(Pure.) High-frequency bursts away from onsets, per second: 5-ms frames of energy above `hf_hz` at least
    `burst_rise_db` over the running median of `burst_median_s`, more than `burst_onset_s` from every onset."""
    import numpy as np
    import scipy.ndimage as nd

    render = mono(render)
    n = int(c["burst_frame_s"] * rate)
    e = _frames_db(render, n, c["hf_hz"])
    if not len(e):
        return 0.0
    med = nd.median_filter(e, size=max(3, int(c["burst_median_s"] / c["burst_frame_s"]) | 1), mode="nearest")
    hit = np.nonzero(e >= med + c["burst_rise_db"])[0]
    on = np.asarray(sorted(onsets_s))
    far = [j for j in hit if not len(on) or np.min(np.abs(on - (j + 0.5) * n / rate)) > c["burst_onset_s"]]
    return len(far) / (len(render) / rate)


def check_dry(true_di, dry, notes, arm, bank=None, rate=NR.SR, c=PRECHECK):
    """One dry guitar's pre-checks against the true DI. notes: the notes it was built from (after the onset step);
    bank: the note bank (nr-plain's level check). -> {checks..., ok, why}."""
    import numpy as np

    why = []
    finite = bool(np.isfinite(dry).all())
    peak = float(np.abs(dry).max()) if finite else None
    peak_true = float(np.abs(true_di).max())
    peak_over = 20 * math.log10((peak + 1e-12) / (peak_true + 1e-12)) if finite else None
    flags = []
    if not finite:
        why.append("non-finite samples")
    elif peak_over > c["peak_over_true_db"]:
        flags.append(f"peak {peak_over:+.1f} dB over the true DI's")
    td = tuning_diff(NR.global_tuning_cents(dry, rate), NR.global_tuning_cents(true_di, rate)) if finite else None
    if td is not None and abs(td) > c["tuning_cents"]:
        why.append(f"tuning {td:+.1f} cents from the true DI")
    gf = gap_floor_diff(true_di, dry, rate, c) if finite else None
    if gf is not None and gf > c["gap_floor_over_true_db"]:
        why.append(f"floor above 3 kHz in the gaps {gf:+.1f} dB over the true DI's")
    ls = level_spread(NR.clean_notes(notes)[0], bank, len(dry), rate) if finite and arm == "nr-plain" and bank \
        else None
    if ls is not None and ls > c["level_spread_db"]:
        why.append(f"onset-group level spread {ls:.1f} dB")
    return {"peak": peak, "peak_over_true_db": peak_over, "tuning_diff_cents": td, "gap_floor_diff_db": gf, "level_spread_db": ls,
            "ok": not why, "why": why, "flags": flags}


def check_bursts(true_render, dry_render, onsets_s, rate=NR.SR, c=PRECHECK):
    """(Pure.) A crunch render's bursts against the true DI's render through the same preset. -> {rates, ok, why}."""
    bt, bd = burst_rate(true_render, onsets_s, rate, c), burst_rate(dry_render, onsets_s, rate, c)
    ok = bd <= bt + c["burst_rate_over_true"]
    return {"burst_rate_true": bt, "burst_rate_dry": bd, "ok": ok,
            "why": [] if ok else [f"bursts {bd:.2f}/s against the true DI's {bt:.2f}/s"]}


PRECHECK_MAX_SHARE = 0.10               # render is refused when more than this share of a deciding arm's parts fail
DECIDING_ARMS = ("nr-plain", "nr-level")


def blocking_why(p, c=PRECHECK):
    """(Pure.) A stored pre-check record's blocking failures under the rules as amended on 2026-11-20 (the peak is
    report only), re-derived from its stored figures, so build.json, written once, is read under the amended rule."""
    why = []
    if p.get("peak") is None:
        why.append("non-finite samples")
    td, gf, ls = p.get("tuning_diff_cents"), p.get("gap_floor_diff_db"), p.get("level_spread_db")
    if td is not None and abs(td) > c["tuning_cents"]:
        why.append(f"tuning {td:+.1f} cents from the true DI")
    if gf is not None and gf > c["gap_floor_over_true_db"]:
        why.append(f"hiss floor {gf:+.1f} dB over the true DI's")
    if ls is not None and ls > c["level_spread_db"]:
        why.append(f"plain-group level spread {ls:.1f} dB")
    return why


def flagged(p, c=PRECHECK):
    """(Pure.) A stored record's report-only flags: its peak more than `peak_over_true_db` over the true DI's."""
    po = p.get("peak_over_true_db")
    return [f"peak {po:+.1f} dB over the true DI's"] if po is not None and po > c["peak_over_true_db"] else []


def precheck_failures(build, kind="blocking"):
    """(Pure.) {arm: [part key]} of the build's dry guitars that fail a blocking pre-check (`kind` "blocking"), or
    that fail one or carry a report-only flag (`kind` "any": the beside row's set), every arm."""
    out = {a: [] for a in NR.ARMS}
    for k, r in sorted(build["parts"].items()):
        for a, x in r["arms"].items():
            p = x.get("precheck") or {}
            if blocking_why(p) or (kind == "any" and flagged(p)):
                out.setdefault(a, []).append(k)
    return out


def precheck_refusal(build, clips_index, max_share=PRECHECK_MAX_SHARE):
    """(Pure.) Why `render` may not start on the pre-checks, or None. Declared 2026-11-20 before `build` (PR #528's
    re-review): refused on any failing clip check (the clips are what the user hears), or when more than `max_share`
    of a deciding arm's parts fail (a systematic fault); `nr-oracle`'s failures never block. Otherwise render goes on,
    each failure is listed, and `score` reads every row beside without the failing parts (`without_precheck_fail`)."""
    if build is None:
        return "run `build` first"
    if clips_index is None:
        return "run `clips` first"
    checks = clips_index.get("checks") or []
    badc = [c["file"] for c in checks if not c.get("ok")]
    if not checks or badc:
        return f"the clips' pre-checks fail ({len(badc)}: {badc[:3]}) or are missing"
    n = len(build["parts"])
    fails = precheck_failures(build)
    for a in DECIDING_ARMS:
        if n and len(fails.get(a, [])) > max_share * n:
            return f"{len(fails[a])} of {n} {a} dry guitars fail a pre-check: a systematic fault (over {max_share:.0%})"
    return None


# --- main's ledger and code -----------------------------------------------------------------------------------------------

def _git(*a):
    import subprocess

    return subprocess.run(["git", "-C", str(NR.REPO), *a], capture_output=True, text=True)


def main_entries():
    """(main's `note-rebuild` entry, main's `preset-ladder` entry, refusal or None): after a fetch, the code files must
    equal main's and this checkout's `note-rebuild` phase keys main's."""
    _git("fetch", "-q", "origin", "main")
    led = _git("show", "origin/main:docs/dev-test-ledger.json")
    if led.returncode:
        return None, None, f"main's ledger is not readable: {led.stderr.strip()}"
    d = json.loads(led.stdout)
    nr = next((t for t in d["tests"] if t["test_id"] == LEDGER_ID), None)
    rp = next((t for t in d["tests"] if t["test_id"] == REPLAY_LEDGER), None)
    for f in CODE_FILES:
        if _git("diff", "--quiet", "origin/main", "--", f).returncode:
            return nr, rp, f"this checkout's {f} differs from main's: run from merged code"
    local = NR.ledger_entry() or {}
    a = {k: v for k, v in local.items() if k.startswith("phase_nr")}
    b = {k: v for k, v in (nr or {}).items() if k.startswith("phase_nr")}
    if a != b:
        return nr, rp, "this checkout's phase_nr keys differ from main's: pull main"
    return nr, rp, None


def require(*phases):
    """Refuse unless this checkout's `note-rebuild` entry holds every phase."""
    for k in phases:
        NR.require(k)


def require_main(*phases):
    nr, rp, why = main_entries()
    if why:
        raise SystemExit(why)
    for k in phases:
        if k not in (nr or {}):
            raise SystemExit(f"main's {LEDGER_ID} entry has no {k}: merge it before running")
    return nr, rp


def require_file_hash(nr, phase, path):
    rec = (nr or {}).get(phase)
    sha = NR.file_sha(path)
    if not isinstance(rec, dict) or rec.get("sha256") != sha:
        raise SystemExit(f"{path.name}'s sha256 {sha[:12]} is not main's {phase}")
    return json.loads(pathlib.Path(path).read_text())


def replay_reports():
    from learn import note_replay as R

    a, b = R.report_path(), R.report_path(singles=True)
    return (json.loads(a.read_text()) if a.exists() else None, json.loads(b.read_text()) if b.exists() else None)


def require_gate(nr, rp):
    report, singles = replay_reports()
    why = gate_refusal(report, rp, nr, singles)
    if why:
        raise SystemExit(f"the gate is closed: {why}")
    return deciding_outcome(report, singles)[0]


# --- the commands ----------------------------------------------------------------------------------------------------------

def cmd_subset(_args):
    """The carrying subset (zero renders, no held-half value): the replay's drawn GOAT parts that carry true notes, from
    the replay's hashed draw and stage P's true-notes.json. -> stage1/subset.json; its sha256 goes into the ledger as
    phase_nr_1_subset before `build` or any render."""
    require(PHASE_1)
    require_main(PHASE_1)
    NR.refuse_existing(subset_path())
    from learn import note_replay as R              # after the refusals

    draw = R.require_draw()
    tn = NR.load_doc("true-notes.json")
    keep, out = carrying_subset(draw["parts"], tn["units"])
    why = subset_refusal(R.file_sha(R.draw_path()), [k["pkey"] for k in keep],
                         true_notes_sha=NR.file_sha(NR.OUT / "true-notes.json"))
    if why:
        raise SystemExit(why)
    for k in keep:
        rec = tn["items"][k["item"]]
        k["notes_sha256"] = rec["notes_sha256"]
        k["notes_file_sha256"] = NR.file_sha(NR.OUT / "true-notes" / f"{k['item']}.json")
        u = tn["units"][f"{k['unit']}|{k['amp']}"]
        for f in ("cls", "fold", "alignment_f", "guitar", "tuning", "player", "tab_share", "articulated", "notes"):
            k[f] = u.get(f)
        k["reader_ok"] = (rec.get("reader_check") or {}).get("ok")
    doc = {"plan": NR.PLAN, "ledger": f"{LEDGER_ID} {PHASE_1}", "draw_sha256": R.file_sha(R.draw_path()),
           "true_notes_body_sha256": NR.content_sha(tn), "parts": keep, "left_out": out,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    NR.write_once(subset_path(), doc)
    print(f"SUBSET: {len(keep)} carrying, {len(out)} left out; sha256 {NR.file_sha(subset_path())} "
          f"(into the ledger as {PHASE_SUBSET} before anything else)")


def require_subset(nr):
    from learn import note_replay as R

    sub = require_file_hash(nr, PHASE_SUBSET, subset_path())
    if sub["draw_sha256"] != R.file_sha(R.draw_path()):
        raise SystemExit("subset.json was made from another draw")
    return sub


def load_item_notes(k):
    """One subset part's notes, refused unless the file is the one hashed into the subset."""
    p = NR.OUT / "true-notes" / f"{k['item']}.json"
    if NR.file_sha(p) != k["notes_file_sha256"]:
        raise SystemExit(f"{p.name}: not the note file the subset hashed")
    rec = json.loads(p.read_text())
    if NR.content_sha(rec["notes"]) != k["notes_sha256"]:
        raise SystemExit(f"{p.name}: its notes are not the subset's")
    return rec["notes"]


def cmd_build(_args):
    """The dry guitars (CPU, zero renders, no held-half value): per subset part, the true DI section as the replay
    renders it (`note_replay.di_section`), the window's true notes moved by the oracle onset step against it, the clean
    record on the section's timeline (`ref_on_section`), and the three arms through `note_rebuild.rebuild_dry` with the
    blurred row's chain as `finish` (`song_bank.measure`, then `di_robustness.average_balance` with the part's
    `others`, the replay's `others_for`); every arm at -22.9 LUFS. The figures against the true DI as rendered beside.
    -> stage1/di/<arm>/<part>.npy, stage1/build.json."""
    require(PHASE_1, PHASE_SUBSET)
    nr, _ = require_main(PHASE_1, PHASE_SUBSET)
    NR.refuse_existing(build_path())
    sub = require_subset(nr)
    import numpy as np                              # after the refusals

    from learn import di_robustness as DR
    from learn import knob_ceiling as K
    from learn import note_replay as R
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as SB

    draw = R.require_draw()
    sd = R.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    bank = NR.Bank(NR.load_notes_doc())
    by = {p["pkey"]: p for p in draw["parts"]}
    by_sec = {}
    for p in draw["parts"]:
        by_sec.setdefault(p["section"], sd.units[(p["set"], p["unit"], p["amp"])]["prt"])
    cache = {}

    def sec(s):
        if s not in cache:
            cache[s] = np.asarray(R.di_section(by_sec[s]), np.float64)
        return cache[s]
    trim = int(PS.TRIM_S * PS.SR)
    out, t0 = {"plan": NR.PLAN, "subset_sha256": NR.file_sha(subset_path()), "parts": {}}, time.time()
    for n_, k in enumerate(sub["parts"]):
        p = by[k["pkey"]]
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        di = sec(p["section"])
        n = len(di)
        notes = NR.window_notes(load_item_notes(k), k["window_s"] - PS.TRIM_S, n / PS.SR)
        offset = NR.coarse_offset(notes, di)
        refined, shifts = NR.refine_onsets(NR.shifted_notes(notes, offset), di)
        clean = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        ref = ref_on_section(np.asarray(clean, np.float64), n, trim, K.P.LATENCY + p["lag"])
        others = {s: [sec(x) for x in xs] for s, xs in R.others_for(p, draw["parts"]).items()}

        def finish(y, others=others):
            return DR.average_balance(SB.measure(y), others)
        rec = {"notes": len(notes), "window_offset_ms": 1000 * offset,
               "onset_shift_ms": {"median": 1000 * float(np.median(np.abs(shifts))) if shifts
                                                       else None, "moved": sum(s != 0 for s in shifts),
                                                       "groups": len(shifts)},
               "arms": {}}
        for arm in NR.ARMS:
            y, rep = NR.rebuild_dry(arm, refined, n, bank, ref, di=di, finish=finish)
            y32 = np.asarray(y, np.float32)
            if len(y32) != n or not np.isfinite(y32).all():
                raise SystemExit(f"{k['pkey']}: a bad {arm} dry guitar")
            path = dry_path(arm, k["pkey"])
            NR.refuse_existing(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            np.save(path, y32)
            rec["arms"][arm] = {"sha256": NR.file_sha(path), "report": rep, "figures": NR.figures(di, y),
                                "precheck": check_dry(di, np.asarray(y32, np.float64), refined, arm, bank)}
        out["parts"][k["pkey"]] = rec
        if n_ % 10 == 0:
            print(f"build {n_ + 1}/{len(sub['parts'])}: {(time.time() - t0) / (n_ + 1):.1f} s each", flush=True)
    NR.write_once(build_path(), out)
    bad = [(k, a, x["precheck"]["why"]) for k, r in out["parts"].items() for a, x in r["arms"].items()
           if not x["precheck"]["ok"]]
    print(f"BUILD DONE: {len(out['parts'])} parts x {len(NR.ARMS)} arms, {time.time() - t0:.0f} s; "
          f"pre-checks failing {len(bad)}{': ' + str(bad[:3]) if bad else ''}; sha256 {NR.file_sha(build_path())}")


def load_arm(arm, pkey, build):
    import numpy as np

    path = dry_path(arm, pkey)
    if NR.file_sha(path) != build["parts"][pkey]["arms"][arm]["sha256"]:
        raise SystemExit(f"{path.name}: not the dry guitar `build` wrote")
    return np.load(path).astype(np.float32)


def cmd_gate(_args):
    """Prints the gate's reading (refuses nothing; reads main's ledger and the replay's report)."""
    from learn import note_replay as R

    nr, rp, why = main_entries()
    report, singles = replay_reports()
    g = gate_refusal(report, rp, nr, singles)
    print(json.dumps({"code_on_main": why is None, "why_not": why, "gate": "go" if g is None else g,
                      "ear": ear_refusal(nr) or "ok"}, indent=1))


def clip_items(meta_items, excl, used, seed=CLIP_SEED, k=CLIP_ITEMS):
    """(Pure but for `clear_of`.) The ear check's development items: GOAT items with fine-aligned MIDI, clear of the
    exclusion list and not among `used`, a seeded sample of k."""
    pool = sorted(it for it in meta_items if not NR.clear_of({"goat_item": it}, excl) and it not in used)
    return sorted(random.Random(f"{seed}|clips").sample(pool, min(k, len(pool))))


def cmd_clips(_args):
    """The ear check before stage 1 (the plan review's item 3): CLIP_ITEMS development GOAT items clear of the
    exclusion list (seeded), a 10-s window each; the true DI (through `song_bank.measure`), `nr-plain` and `nr-level`
    (finished by `song_bank.measure`), each through the clean and crunch class starts S on CLIP_AMP, each render primed
    alone: 4 x 3 x 2 = 24 kept, 48 renders; each clip set to CLIP_LUFS (loudness matched), guitar only. It reads only
    development items, so it does not wait for the replay's outcome; it takes a render slot (waiting for the replay's
    renders) and never runs beside a separation. The pre-checks (`check_dry` on each dry guitar, `check_bursts` on each
    crunch render against the true DI's) go into the index. -> ~/ndsp-presets/listening/note-rebuild-ear/
    <item>-<dry>-<cls>.wav, index.json. The user's verdict goes into the ledger as phase_nr_1_ear ("ok", or "fault"
    with what was heard); `pick` and `score` refuse without "ok"."""
    require(PHASE_1, PHASE_SUBSET)
    require_main(PHASE_1, PHASE_SUBSET)
    dest = clips_dir()
    NR.refuse_existing(dest)
    from learn import note_replay as R              # after the refusals

    R.no_separation_beside()
    import csv                                      # after the refusals
    import io
    import zipfile

    import numpy as np
    import soundfile as sf

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import clean_di as CD
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as SB

    excl = NR.load_exclusion()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    ms = P.A_menu_S()[CLIP_AMP]
    sec = int(round((PS.SEC_S + PS.TRIM_S) * PS.SR))
    trim = (int(PS.TRIM_S * PS.SR), sec)
    LO._wait_cap()
    index = {"plan": NR.PLAN, "amp": CLIP_AMP, "lufs": CLIP_LUFS, "clips": [], "checks": []}
    with zipfile.ZipFile(NR.GOAT_ZIP) as z:
        names = set(z.namelist())
        meta = {r["item"]: r for r in csv.DictReader(io.StringIO(z.read("GOAT/metadata.csv").decode()))}
        items = clip_items([it for it in meta if f"GOAT/data/{it}/{it}_fine_aligned.mid" in names], excl, set())
        NR.assert_clear([{"goat_item": it} for it in items], excl)
        dest.mkdir(parents=True)
        for it in items:
            rec = NR.true_notes_for(it, z, meta)
            x, sr = sf.read(io.BytesIO(z.read(f"GOAT/data/{it}/{it}.wav")), dtype="float64", always_2d=True)
            x = CD.resample(x.mean(1), sr, PS.SR)
            start = 30.0 if len(x) / PS.SR > 45 else 1.0
            di = SB.measure(x[int(start * PS.SR):int(start * PS.SR) + sec])
            wn = NR.window_notes(rec["notes"], start, sec / PS.SR)
            notes, _ = NR.refine_onsets(NR.shifted_notes(wn, NR.coarse_offset(wn, di)), di)
            drys = {"true": di}
            for arm in ("nr-plain", "nr-level"):
                drys[arm], _ = NR.rebuild_dry(arm, notes, sec, bank, di, finish=SB.measure)
                c = check_dry(di, drys[arm], notes, arm, bank)
                index["checks"].append({"file": f"{it}-{arm} (dry)", **c})
            onsets = [n["on"] - PS.TRIM_S for n in notes]
            for cls in ("clean", "crunch"):
                sel, S = ms[cls]
                s_ = LO.tdict(LO.sdict(dict(S)))
                rendered = {}
                for dname, y in drys.items():
                    out = np.asarray(AM.fresh_render(CB.new_renderer, np.asarray(y, np.float32), sel, s_, s_),
                                     np.float64)[trim[0]:trim[1]]
                    if not np.isfinite(out).all():
                        raise SystemExit(f"{it} {dname} {cls}: a non-finite render")
                    rendered[dname] = out
                    f = dest / f"{it}-{dname}-{cls}.wav"
                    clip = NR.at_lufs(out, CLIP_LUFS)
                    sf.write(f, clip.astype(np.float32), PS.SR)
                    index["clips"].append({"item": it, "dry": dname, "cls": cls, "file": f.name,
                                           "peak": float(np.abs(clip).max()), "sha256": NR.file_sha(f)})
                if cls == "crunch":
                    for arm in ("nr-plain", "nr-level"):
                        index["checks"].append({"file": f"{it}-{arm}-crunch",
                                                **check_bursts(rendered["true"], rendered[arm], onsets)})
    index["all_ok"] = all(c["ok"] for c in index["checks"])
    NR.write_once(dest / "index.json", index)
    print(f"CLIPS DONE: {len(index['clips'])} clips in {dest}; pre-checks "
          f"{'pass' if index['all_ok'] else 'FAIL: ' + str([c for c in index['checks'] if not c['ok']][:3])}")


def cmd_render(args):
    """One shard's renders (after the gate and the ear check): each subset part's three arms through its 23 menu
    settings in the replay's position-check mode (`note_replay.render_menu`), each kept render's search-half distance
    against the clean record (`note_replay.half_distance`, the dry guitar as the judge's DI), no held-half distance, no
    audio kept. Refused unless every pre-check passes (`precheck_refusal`: the build's and the clips'). The ear check
    gates `pick`, not `render`: renders read nothing, and a heard fault discards them under a declared revision before
    any read. -> stage1/dist/<arm>/<part>.json."""
    require(PHASE_1, PHASE_SUBSET)
    nr, rp = require_main(PHASE_1, PHASE_SUBSET)
    require_gate(nr, rp)
    sub = require_subset(nr)
    build = json.loads(build_path().read_text()) if build_path().exists() else None
    ci = clips_dir() / "index.json"
    why = precheck_refusal(build, json.loads(ci.read_text()) if ci.exists() else None)
    if why:
        raise SystemExit(why)
    fl = {a: v for a, v in precheck_failures(build, "any").items() if v}
    if fl:
        print(f"pre-check failures and flags (rendered; read beside without them): {json.dumps(fl)}", flush=True)
    if build["subset_sha256"] != NR.file_sha(subset_path()):
        raise SystemExit("build.json was made from another subset")
    from learn import note_replay as R              # after the refusals

    pos = R.control_path("position")
    if not pos.exists():
        raise SystemExit("the replay's position check is missing")
    mode = json.loads(pos.read_text())["mode"]
    R.no_separation_beside()
    import numpy as np

    from learn import audibility_measure as AM
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    draw = R.require_draw()
    sd = R.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    by = {p["pkey"]: p for p in draw["parts"]}
    k_, n_ = args.shard
    mine = [k for j, k in enumerate(sorted(x["pkey"] for x in sub["parts"])) if j % n_ == k_]
    LO._wait_cap()
    renders, t0 = 0, time.time()
    for key in mine:
        p = by[key]
        todo = [a for a in NR.ARMS if not dist_path(a, key).exists()]
        if not todo:
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        _, clean, trim = R.part_audio(sd, p)
        for arm in todo:
            t1 = time.time()
            x32 = load_arm(arm, key, build)
            dj = np.asarray(x32, np.float64)[trim[0]:trim[1]]
            ys, used = R.render_menu(x32, p["menu"], mode)
            renders += used
            rec = {"plan": NR.PLAN, "part": key, "arm": arm, "mode": mode, "lag": p["lag"], "search": p["search"],
                   "menu_sha256": hashlib.sha256(json.dumps(p["menu"], sort_keys=True).encode()).hexdigest(),
                   "distances": [R.half_distance(clean, y, dj, p["lag"], p["search"]) for y in ys],
                   "render_sha256": [AM.audio_sha(y) for y in ys], "renders": used, "seconds": time.time() - t1}
            path = dist_path(arm, key)
            NR.write_once(path, rec)
        print(f"{key[-60:]}: renders so far {renders}, {time.time() - t0:.0f} s", flush=True)
    print(f"NR1-RENDER DONE {k_}/{n_}: {renders} renders in {time.time() - t0:.0f} s")


def load_dist(arm, p):
    path = dist_path(arm, p["pkey"])
    if not path.exists():
        return None
    rec = json.loads(path.read_text())
    if rec["menu_sha256"] != hashlib.sha256(json.dumps(p["menu"], sort_keys=True).encode()).hexdigest():
        raise SystemExit(f"{path.name}: rendered from another menu")
    return rec


def cmd_pick(_args):
    """The picks (zero renders; distances only): per arm and subset part the menu position with the smallest
    search-half distance (`note_replay.pick_index`). -> stage1/picks.json; its sha256 goes into the ledger as
    phase_nr_1_picks before `score`."""
    require(PHASE_1, PHASE_SUBSET, PHASE_EAR)
    nr, rp = require_main(PHASE_1, PHASE_SUBSET, PHASE_EAR)
    require_gate(nr, rp)
    sub = require_subset(nr)
    NR.refuse_existing(picks_path())
    why = ear_refusal(nr)
    if why:
        raise SystemExit(why)
    from learn import note_replay as R

    draw = R.require_draw()
    by = {p["pkey"]: p for p in draw["parts"]}
    out = {"plan": NR.PLAN, "subset_sha256": NR.file_sha(subset_path()), "rows": {}, "dist_sha256": {},
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    for arm in NR.ARMS:
        out["rows"][arm] = {}
        for k in sub["parts"]:
            rec = load_dist(arm, by[k["pkey"]])
            if rec is None:
                raise SystemExit(f"{k['pkey']}: no {arm} renders")
            out["dist_sha256"][f"{arm}/{k['pkey']}"] = NR.file_sha(dist_path(arm, k["pkey"]))
            out["rows"][arm][k["pkey"]] = {"pick": R.pick_index(rec["distances"]),
                                           "pick_nl": R.pick_index(rec["distances"], skip=(R.LABEL_INDEX,))}
    NR.write_once(picks_path(), out)
    print(f"NR1-PICKS: {len(sub['parts'])} parts x {len(NR.ARMS)} arms; sha256 {NR.file_sha(picks_path())} "
          f"(into the ledger as {PHASE_PICKS} before `score`)")


def breakdowns(sub_parts, per, band_rows):
    """The arm's breakdowns at no render cost: by alignment-F tertile, Strat or not, tab-matched share at 0.8 or more,
    articulated share at or below the subset's median, clean or crunch. per: {pkey: part numbers}; band_rows: a
    function (parts, values) -> the GOAT row. -> {name: {group: {G, I}}}."""
    import statistics

    edges = tertile_edges([k["alignment_f"] for k in sub_parts])
    arts = [k["articulated"] for k in sub_parts if k["articulated"] is not None]
    med = statistics.median(arts) if arts else None
    splits = {
        "alignment_f_tertile": lambda k: group_of(k["alignment_f"], edges),
        "strat": lambda k: k["guitar"] == "strat",
        "tab_share_0.8": lambda k: (k["tab_share"] or 0) >= NR.CARRY_TAB_SHARE,
        "articulated_low": lambda k: None if med is None or k["articulated"] is None else k["articulated"] <= med,
        "cls": lambda k: k["cls"]}
    out = {"alignment_f_edges": edges, "articulated_median": med}
    for name, f in splits.items():
        groups = {}
        for k in sub_parts:
            groups.setdefault(str(f(k)), []).append(k["pkey"])
        out[name] = {g: {q: band_rows(ks, {k: (per.get(k) or {}).get(q) for k in ks}) for q in ("G", "I")}
                     for g, ks in sorted(groups.items())}
    return out


def safe_reading(g, i):
    """(Pure.) `note_rebuild.row_reading`, or None when either row has no interval (so a read never crashes after its
    rows are saved)."""
    try:
        return NR.row_reading(g, i)
    except ValueError:
        return None


def n1_outcome(readings):
    """(Pure.) N1_TABLE's code and next from the arms' readings; "N1-incomplete" when a deciding arm has no reading."""
    p, lv = readings.get("nr-plain"), readings.get("nr-level")
    if p is None or lv is None:
        return {"code": "N1-incomplete", "next": "a deciding arm has no interval: nothing is read; to the orchestrator",
                "arm": None}
    code = NR.n1_code(p, lv)
    return {"code": code, "next": dict((c, t) for c, _, t in NR.N1_TABLE)[code], "arm": NR.n1_arm(p, lv)}


def beside_sets(sub_parts, failures=None, flags=None):
    """(Pure.) The beside rows' part keys: without the alignment-F 0.0 part, without the parts whose item fails its own
    MIDI reader check (stage P's `reader_check`), without the parts where nr-plain or nr-level fails a blocking
    pre-check (`precheck_failures`), and without those where either carries the report-only peak flag (`flags`:
    {arm: [part key]}). One set for every row."""
    bad = {k for a in DECIDING_ARMS for k in (failures or {}).get(a, [])}
    peaky = {k for a in DECIDING_ARMS for k in (flags or {}).get(a, [])}
    return {BESIDE_F0: without_f0(sub_parts),
            BESIDE_READER: [k["pkey"] for k in sub_parts if k.get("reader_ok") is not False],
            BESIDE_PRECHECK: [k["pkey"] for k in sub_parts if k["pkey"] not in bad],
            BESIDE_PEAK: [k["pkey"] for k in sub_parts if k["pkey"] not in peaky]}


def peak_flags(build):
    """(Pure.) {arm: [part key]} whose stored pre-check carries the report-only peak flag."""
    out = {a: [] for a in NR.ARMS}
    for k, r in sorted(build["parts"].items()):
        for a, x in r["arms"].items():
            if flagged(x.get("precheck") or {}):
                out.setdefault(a, []).append(k)
    return out


def cmd_score(_args):
    """The read (zero renders), once: refused unless picks.json's sha256 is main's phase_nr_1_picks and the ear check
    reads ok. Per arm: each part's numbers (`note_replay.part_numbers` on the stored held-half scores), the GOAT row of
    G and I (`note_replay.summary`'s `goat`: GOAT items as clusters), its reading (`note_rebuild.row_reading`); beside,
    the replay's GOAT-alone Control and comparison rows recomputed on exactly the subset from the replay's own distance
    files (each file's sha256 checked against the replay's hashed picks): Control (the true DI) and Blurred (the dry
    guitar the replay's deciding outcome rests on, `comparison_dry`; a second passing single blur beside), each arm's
    share of the Blurred row's I, the breakdowns, the label-free numbers, the Spearman with the true DI's distances,
    the beside rows without the alignment-F 0.0 part and without the reader-check failures. The rows are saved before
    N1_TABLE's code is read. -> stage1/report-rows.json, then stage1/report.json."""
    require(PHASE_1, PHASE_SUBSET, PHASE_EAR, PHASE_PICKS)
    nr, rp = require_main(PHASE_1, PHASE_SUBSET, PHASE_EAR, PHASE_PICKS)
    outcome = require_gate(nr, rp)
    why = ear_refusal(nr)
    if why:
        raise SystemExit(why)
    sub = require_subset(nr)
    picks = require_file_hash(nr, PHASE_PICKS, picks_path())
    NR.refuse_existing(report_path())
    NR.refuse_existing(rows_path())
    NR.table_guard()
    from learn import note_replay as R

    draw = R.require_draw()
    sd = R.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    by = {p["pkey"]: p for p in draw["parts"]}
    parts = [by[k["pkey"]] for k in sub["parts"]]
    band = R.lender_band()
    main_dry, beside_dry = comparison_dry(outcome)
    rpicks = {"main": json.loads(R.picks_path().read_text())}
    if R.picks_path(singles=True).exists():
        rpicks["singles"] = json.loads(R.picks_path(singles=True).read_text())

    def replay_dist(dry, p):
        which = "singles" if dry in R.SINGLE_DRY else "main"
        want = (rpicks.get(which) or {}).get("dist_sha256", {}).get(f"{dry}/{p['pkey']}")
        if want is None or R.file_sha(R.dist_path(dry, p["pkey"])) != want:
            raise SystemExit(f"{dry}/{p['pkey']}: not the distance file the replay's picks hashed")
        return R.load_dist(dry, p)["distances"]["clean"]

    def goat_row(keys, values):
        return R.summary(sd.units, [by[k] for k in keys], values, band)["goat"]
    build = json.loads(build_path().read_text())
    if build["subset_sha256"] != NR.file_sha(subset_path()):
        raise SystemExit("build.json was made from another subset")
    failures = precheck_failures(build)
    besides = beside_sets(sub["parts"], failures, peak_flags(build))

    def with_besides(per, qs):
        keys = [p["pkey"] for p in parts]
        return {**{q: goat_row(keys, {k: (v or {}).get(q) for k, v in per.items()}) for q in qs},
                **{name: {q: goat_row(ks, {k: (per.get(k) or {}).get(q) for k in ks}) for q in ("G", "I")}
                   for name, ks in besides.items()}}
    hs = {p["pkey"]: R.h_of(sd.held((p["set"], p["unit"], p["amp"]), p["menu"])) for p in parts}
    true_d = {p["pkey"]: replay_dist("true", p) for p in parts}
    rows = {}
    for name, dry in [("control", "true"), ("blurred", main_dry)] + [(f"blurred:{d}", d) for d in beside_dry]:
        per = {p["pkey"]: R.part_numbers(replay_dist(dry, p), hs[p["pkey"]]) for p in parts}
        rows[name] = {"dry": dry, "parts": per, **with_besides(per, ("G", "I", "blind"))}
    for arm in NR.ARMS:
        per = {}
        for p in parts:
            d = load_dist(arm, p)["distances"]
            num = R.part_numbers(d, hs[p["pkey"]])
            if num is not None and (num["pick"] != picks["rows"][arm][p["pkey"]]["pick"]
                                    or num["pick_nl"] != picks["rows"][arm][p["pkey"]]["pick_nl"]):
                raise SystemExit(f"{arm} {p['pkey']}: the distances' pick is not the hashed pick")
            if num is not None:
                num["spearman_vs_true"] = R.spearman(d, true_d[p["pkey"]])
                num["refused_windows"] = sum(not math.isfinite(x) for x in d)
            per[p["pkey"]] = num
        rows[arm] = {"parts": per, **with_besides(per, ("G", "I", "G_nl", "I_nl")),
                     "breakdowns": breakdowns(sub["parts"], per, goat_row),
                     "no_pick": sorted(k for k, v in per.items() if v is None)}
    out = {"plan": NR.PLAN, "ledger": f"{LEDGER_ID} {PHASE_1}", "subset_sha256": NR.file_sha(subset_path()),
           "picks_sha256": NR.file_sha(picks_path()), "replay_outcome": outcome, "comparison_dry": main_dry,
           "precheck_failures": failures, "peak_flags": peak_flags(build),
           "time": time.strftime("%Y-%m-%d %H:%M:%S"), "rows": rows}
    NR.write_once(rows_path(), out)                    # the rows are saved before the code is read
    readings = {arm: safe_reading(rows[arm]["G"], rows[arm]["I"]) for arm in NR.ARMS}
    bl = rows["blurred"]["I"].get("mean")
    shares = {arm: (rows[arm]["I"].get("mean") / bl if bl and rows[arm]["I"].get("mean") is not None else None)
              for arm in NR.ARMS}
    final = {**out, "readings": readings, "share_of_blurred_I": shares, **n1_outcome(readings)}
    final["confound_sharper_attack"] = {           # declared 2026-11-20: compared on N1-fail or N1-between
        "note": PEAK_CONFOUND, "applies": final["code"] in ("N1-fail", "N1-between"),
        "rows": {arm: {"full": {q: rows[arm][q] for q in ("G", "I")}, BESIDE_PEAK: rows[arm][BESIDE_PEAK],
                       "reading_full": readings[arm],
                       "reading_without_peak_flag": safe_reading(rows[arm][BESIDE_PEAK]["G"],
                                                                 rows[arm][BESIDE_PEAK]["I"])}
                 for arm in NR.ARMS}}
    NR.write_once(report_path(), final)
    for arm in NR.ARMS:
        g, i = rows[arm]["G"], rows[arm]["I"]
        print(f"{arm}: G {g.get('mean')} [{g.get('lo90')}, {g.get('hi90')}], I {i.get('mean')} [{i.get('lo90')}, "
              f"{i.get('hi90')}] -> {readings[arm]}{' (diagnostic)' if arm == 'nr-oracle' else ''}")
    print(f"N1 {final['code']}: {final['next']}")


def _shard(s):
    k, n = (int(x) for x in s.split("/"))
    if not 0 <= k < n or n > 3:
        raise argparse.ArgumentTypeError("k/n with 0 <= k < n <= 3 (at most 3 render processes)")
    return k, n


COMMANDS = {"subset": cmd_subset, "build": cmd_build, "gate": cmd_gate, "clips": cmd_clips, "render": cmd_render,
            "pick": cmd_pick, "score": cmd_score}


def main(argv=None):
    import sys

    for p_ in (str(NR.REPO), str(NR.REPO / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--shard", type=_shard, default=(0, 1))
    args = ap.parse_args(argv)
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
