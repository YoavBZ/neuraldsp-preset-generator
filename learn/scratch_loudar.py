"""The from-scratch search's `fs-loudar` row, LOUDAR's second test: does a dry guitar rebuilt by LOUDAR from the song's
stem drive the search? (`docs/scratch-search-plan.md` section 13, "The `fs-loudar` row"; ledger `preset-ladder`
`phase_scratch_loudar`, then `phase_scratch_loudar_dry`, `phase_scratch_loudar_answers_stem`, `..._cut`, `..._in`,
and only after `FL-short` or `FL-null` `phase_scratch_loudar_dry_rec` and `..._answers_rec`;
`phase_scratch_loudar_outcome`.)

`fs-loudar` is the codec row's short row (`scratch_codec`) with another dry guitar. LOUDAR (`learn/loudar_run.py`, its
own venv, the CPU) hears only the **search half** of the stored `xlnoG@-3` stem and returns a dry guitar; it is
measured as usual (`song_bank.measure`, on the 4.5-s clip) and placed on the DI's timeline by the stored lag and the
plugin's latency, zeros elsewhere. It drives `run_part(budget=50, step1_only=True)` against the stem with the held half
zeros; `cp50` is scored through the **true DI** on the **held half** against the clean record. Two control rows:
`di-cut` (the raw true DI cut to the same span, then measured the same way) and `stem-in` (the stem's search half
itself, measured, as the dry guitar). BKS and the panel decide (23 parts); GOAT, which LOUDAR's prior trained on, is
read beside, and only if it fits the cost stop.

    $MAIN -m learn.scratch_loudar prep                      # zero renders: the search halves LOUDAR hears
    # LOUDAR's runs in loudar-venv (learn/loudar_run.py's docstring)
    $MAIN -m learn.scratch_loudar build                     # zero renders; -> phase_scratch_loudar_dry
    $MAIN -m learn.scratch_loudar start --name ld-stem --shard 0/3   # 2 renders a part
    $MAIN -m learn.scratch_loudar control                   # 22 renders, once
    $MAIN -m learn.scratch_loudar search --name ld-stem --shard 0/3 [--first 2]
    $MAIN -m learn.scratch_loudar answers --name ld-stem    # -> phase_scratch_loudar_answers_stem
    $MAIN -m learn.scratch_loudar score --name ld-stem --shard 0/3
    $MAIN -m learn.scratch_loudar read                      # once, with ld-stem, di-cut and stem-in scored
    # only after FL-short or FL-null: build-rec, then ld-rec's start, search, answers, score, and read-rec
    $MAIN -m learn.scratch_loudar versus-notes              # zero renders, once fs-notes is read

Every command refuses unless this checkout runs main's code and keys (this module, `learn/loudar_run.py`,
`learn/scratch_codec.py`, `learn/codec_roundtrip.py`; the `phase_scratch_loudar*` keys; `scratch_search.on_main`),
main's blob of `learn/scratch_search.py` is the checked one, and `fs-notes`' two checks stand. Every render command
also waits while `fs-notes` might still run: until its report exists, or main's `phase_nr_1_redo_ear` verdict is
recorded as anything but "ok" (then `fs-notes` will not run). It edits none of
`scratch_search.py`, `scratch_notes.py`, `note_transcribe.py`, `scratch_codec.py` or `codec_roundtrip.py`.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import time

from learn import scratch_codec as SC
from learn import scratch_notes as SN
from learn import scratch_search as S

LEDGER_ID = S.LEDGER_ID
PLAN = "docs/scratch-search-plan.md section 13"
PHASE = "phase_scratch_loudar"
PHASE_DRY = "phase_scratch_loudar_dry"
PHASE_DRY_REC = "phase_scratch_loudar_dry_rec"      # ld-rec's build, only after FL-short or FL-null
PHASE_OUTCOME = "phase_scratch_loudar_outcome"
KEY_PREFIX = "phase_scratch_loudar"
ROW = "fs-loudar"
REF = "xlnoG"
NAMES = ("ld-stem", "ld-stem-b", "ld-rec", "di-cut", "stem-in")
CONTROL_NAME = "di-whole"                          # the control's only: the whole true DI
SEARCHED = ("ld-stem", "di-cut", "stem-in")
REC = "ld-rec"
SHORT = {"ld-stem": "stem", "di-cut": "cut", "stem-in": "in", "ld-rec": "rec"}
PLACED = ("ld-stem", "ld-stem-b", "ld-rec", "stem-in")   # placed on the DI's timeline: the timing check reads these
SOURCES = {"ld-stem": "ld-stem", "ld-stem-b": "ld-stem", "ld-rec": "ld-rec"}   # LOUDAR's runs: name -> in/<src>
DECIDING = ("bks", "panel")
BESIDE = ("goat",)
PANEL_FILES = 3                                    # a lost panel DI file stops the row, to the user
REFUSAL_STOP = 3                                   # of the 23 deciding parts
CODE_FILES = ("learn/scratch_loudar.py", "learn/loudar_run.py", "learn/scratch_codec.py", "learn/codec_roundtrip.py")
SR = 48000
SECTION = 492000
CLIP = 216000
TRIM_N = 12000                                     # the DI section's 0.25 s before (pretrain_set.TRIM_S)
LATENCY = 52                                       # the plugin's (knob_ceiling.P.LATENCY)
HALVES = {"A": (1.0, 5.5), "B": (5.5, 10.0)}       # pretrain_set.HALVES (= knob_ceiling.R.HALVES; a test holds it)
SMALL, BIG = S.SMALL, S.BIG
CUT_SWITCH = 0.05                                  # D_cut's upper end above this: the table reads D_bar
TIMING_MS, TIMING_STOP = 1.0, 3                    # the codec row's rule, as a check: 3 or more deciding parts stop
CHECK_SHA256 = SC.CHECK_SHA256
COMPRESSION_NOTE = SC.COMPRESSION_NOTE


def phase_answers(name):
    if name not in SHORT:
        raise SystemExit(f"{name!r} has no row (only {list(SHORT)})")
    return f"{KEY_PREFIX}_answers_{SHORT[name]}"


# --- the span (pure) -------------------------------------------------------------------------------------------------------

def half_samples(half):
    """(Pure.) The search half's record samples [a, b) (`scratch_search.search_window`'s)."""
    a, b = HALVES[half]
    return int(a * SR), int(b * SR)


def span(p):
    """(Pure.) Where a part's search-half clip goes on the DI section: record sample t goes to DI sample
    t - lag - LATENCY + TRIM_N (the alignment every row uses; the stored lag was estimated against the true DI), cut at
    the section's ends. -> (lo, hi, c0, c1): DI samples [lo, hi) take clip samples [c0, c1)."""
    a, b = half_samples(p["search"])
    off = -int(p["lag"]) - LATENCY + TRIM_N
    lo, hi = a + off, b + off
    c0, c1 = max(0, -lo), (b - a) - max(0, hi - SECTION)
    return max(0, lo), min(SECTION, hi), c0, c1


def place(clip, p):
    """(numpy.) The clip on the DI's timeline: a float32 array of SECTION samples, zeros outside `span`."""
    import numpy as np

    lo, hi, c0, c1 = span(p)
    out = np.zeros(SECTION, np.float32)
    out[lo:hi] = np.asarray(clip, np.float32)[c0:c1]
    return out


# --- the table (pure) ------------------------------------------------------------------------------------------------------

FL_TABLE = (    # (code, when, reading, what follows); the first that holds, on the deciding number
    ("FL-null", "D_null's lower end at -0.05 or above",
     "LOUDAR's dry guitar is not readably better than the stem it was made from",
     "ld-rec runs. LOUDAR is parked. If stem-in itself reaches the bar, that goes to the user as its own finding"),
    ("FL-above", "the deciding number's whole interval below zero, its mean at -0.05 or beyond, and G50(ld-stem)'s "
     "upper end below zero on BKS+panel",
     "from the song's stem alone, LOUDAR's dry guitar beats the blurred true DI at the checkpoint, and beats Cen",
     "the route leads. Proposed next, each under its own declaration: its full row, a stem from a mix with other "
     "guitars, a listen"),
    ("FL-reach", "its upper end under +0.10 and its mean under +0.05",
     "level with the blurred true DI: a heard-size loss is ruled out",
     "to the user with fs-notes beside: the two routes are compared before either goes on"),
    ("FL-short", "its whole interval above zero, its mean at +0.05 or beyond", "below the bar",
     "ld-rec runs and names the bottleneck. The route is parked, not closed"),
    ("FL-undecided", "anything else", "not decided; undecided is not failed", "to the user with the intervals"),
)
FL_CODES = tuple(c for c, *_ in FL_TABLE)
REC_CODES = ("FL-short", "FL-null")                # ld-rec runs after these


def _iv_ok(iv):
    return isinstance(iv, dict) and all(isinstance(iv.get(k), (int, float)) and math.isfinite(iv[k])
                                        for k in ("mean", "lo90", "hi90"))


def deciding_number(d_blur, d_cut, d_bar):
    """(Pure.) `D_blur`, unless the cut itself costs something (`D_cut`'s upper end above +0.05): then `D_bar`.
    -> (name, interval)."""
    if _iv_ok(d_cut) and d_cut["hi90"] > CUT_SWITCH:
        return "D_bar", d_bar
    return "D_blur", d_blur


def fl_holds(d_null, d, g50, small=SMALL, big=BIG):
    """(Pure.) Which of FL_TABLE's conditions hold. d: the deciding number's interval; g50: G50(ld-stem) on
    BKS+panel. `D_true` does not gate: per part D_blur = D_true - ((c) - (b))."""
    return {"FL-null": d_null["lo90"] >= -small,
            "FL-above": d["hi90"] < 0 and d["mean"] <= -small and g50["hi90"] < 0,
            "FL-reach": d["hi90"] < big and d["mean"] < small,
            "FL-short": d["lo90"] > 0 and d["mean"] >= small,
            "FL-undecided": True}


def fl_code(d_null, d_blur, d_cut, d_bar, g50, bar_g50, small=SMALL, big=BIG):
    """(Pure.) FL_TABLE's code, the first that holds. Each argument a pooled row {mean, lo90, hi90} on BKS+panel:
    D_null, D_blur, D_cut, D_bar, G50(ld-stem) and the bar's own G50 (row (c)). -> {code, number (which decided),
    reading, next, heard (FL-above at -0.10 or beyond)}."""
    for nm, iv in (("D_null", d_null), ("D_blur", d_blur), ("D_cut", d_cut), ("D_bar", d_bar), ("G50", g50),
                   ("bar G50", bar_g50)):
        if not _iv_ok(iv):
            raise SystemExit(f"fl_code needs {nm} with a finite mean and 90% interval")
    number, d = deciding_number(d_blur, d_cut, d_bar)
    holds = fl_holds(d_null, d, g50, small, big)
    code = next(c for c in FL_CODES if holds[c])
    w, r, n = {c: (w, r, n) for c, w, r, n in FL_TABLE}[code]
    out = {"code": code, "number": number, "when": w, "reading": r, "next": n, "compression": COMPRESSION_NOTE}
    if code == "FL-above":
        out["heard"] = d["mean"] <= -big
        if not out["heard"]:
            out["reading"] += " (not by a heard size: the mean is short of -0.10)"
    if code == "FL-reach" and bar_g50["hi90"] >= 0:
        out["reading"] += "; level with a bar that is itself level with Cen here"
    if d["hi90"] < 0 and d["mean"] <= -small and code != "FL-above":
        out["gate"] = "the deciding number is above the bar, but G50(ld-stem)'s upper end is not below zero"
    return out


def fl_table_guard():
    """Refuse unless FL_TABLE holds the five codes in order, FL-above and FL-reach cannot hold with FL-short on a grid
    of intervals (lo < mean < hi), and 0 < SMALL < BIG."""
    if FL_CODES != ("FL-null", "FL-above", "FL-reach", "FL-short", "FL-undecided"):
        raise SystemExit("FL_TABLE's codes are not the five declared, in order")
    if not 0 < SMALL < BIG:
        raise SystemExit("the thresholds are not 0 < SMALL < BIG")
    grid = [x / 100 for x in range(-30, 31, 2)]
    g = {"mean": -0.2, "lo90": -0.3, "hi90": -0.1}
    for lo in grid:
        for m in (x for x in grid if x > lo):
            for hi in (x for x in grid if x > m):
                iv = {"mean": m, "lo90": lo, "hi90": hi}
                h = fl_holds(iv, iv, g)
                if h["FL-short"] and (h["FL-above"] or h["FL-reach"]):
                    raise SystemExit(f"FL-short holds with FL-above or FL-reach on {iv}")


def goat_reading(d_blur_goat, small=SMALL, big=BIG):
    """(Pure.) GOAT's beside read (in-sample for the prior): "at the bar" (upper end under +0.10, mean under +0.05),
    "short" otherwise; None when GOAT did not fit the cost stop (not run)."""
    if d_blur_goat is None:
        return None
    if not _iv_ok(d_blur_goat):
        raise SystemExit("goat_reading needs D_blur on GOAT with an interval")
    return "at the bar" if d_blur_goat["hi90"] < big and d_blur_goat["mean"] < small else "short"


def bottleneck(rec_code, goat):
    """(Pure.) After FL-short or FL-null: ld-rec's code by the same table, and GOAT's beside read. ld-rec at or above
    the bar: the stem. Else GOAT at the bar while BKS and the panel are short: the prior's coverage, or memorisation.
    GOAT short too: the generator or its operator. GOAT not run (outside the cost stop): generator against prior: not
    split. A failing part is a research target; nothing is closed."""
    if rec_code not in FL_CODES:
        raise SystemExit(f"bottleneck needs ld-rec's FL code, not {rec_code!r}")
    if rec_code in ("FL-above", "FL-reach"):
        return {"bottleneck": "the stem", "next": "LOUDAR becomes a yardstick for separator work"}
    if goat is None:
        return {"bottleneck": "generator against prior: not split", "next": "GOAT was outside the cost stop"}
    if goat == "at the bar":
        return {"bottleneck": "the prior's coverage, or memorisation",
                "next": "a wider prior would be a build with its own go"}
    return {"bottleneck": "the generator or its operator", "next": "a research target; nothing is closed"}


def slots_refusal(report_exists, ear_record):
    """(Pure.) Why a render command waits for `fs-notes`, or None. The gate keeps the render slots free while
    `fs-notes` might still run; it is not a dependency on `fs-notes` passing. Renders may go once `fs-notes`' report
    exists, or once main's phase_nr_1_redo_ear verdict is recorded as anything but "ok" (then `fs-notes` will not
    run). They wait while there is no report and the verdict is missing or "ok"."""
    if report_exists:
        return None
    verdict = ear_record.get("verdict") if isinstance(ear_record, dict) else None
    if verdict is not None and verdict != "ok":
        return None
    return (f"fs-notes may still run (no PF/fs/notes/report.json; main's phase_nr_1_redo_ear verdict "
            f"{verdict!r}): renders wait for its row")


def pool_refusal(rows):
    """(Pure.) The pool rule on BKS+panel rows {"bks", "panel", "bp"}: both sets read, the panel on its 3 DI files."""
    for s in DECIDING:
        if (rows.get(s) or {}).get("mean") is None:
            return f"{s} is not read"
    if (rows.get("panel") or {}).get("clusters") != PANEL_FILES:
        return f"the panel is read on {(rows.get('panel') or {}).get('clusters')} DI files, not {PANEL_FILES}"
    if not _iv_ok(rows.get("bp")):
        return "BKS+panel has no pooled interval"
    return None


def deciding_stop(refused, sets_of):
    """(Pure.) The refusal stop counts the 23 deciding parts (3 or more stop); GOAT's refusals are listed only."""
    return SN.deciding_stop(refused, sets_of, deciding=DECIDING, stop=REFUSAL_STOP)


def rec_refusal(report):
    """(Pure.) ld-rec runs only after the main read's FL-short or FL-null."""
    code = ((report or {}).get("fl") or {}).get("code")
    if code not in REC_CODES:
        return f"the row reads {code}, not FL-short or FL-null: ld-rec does not run"
    return None


def notes_width(draw_parts):
    """(Pure.) The fs-notes comparison's width on BKS: parts and songs (BKS's DI files are named by song)."""
    bks = [p for p in draw_parts if p["set"] == "bks"]
    songs = {p["cluster"].split("|", 1)[1].split("/")[1] for p in bks}
    return {"parts": len(bks), "songs": len(songs)}


# --- paths -----------------------------------------------------------------------------------------------------------------

def loudar_dir():
    return S.fs_dir() / "loudar"


def in_dir(src):
    return loudar_dir() / "in" / src


def in_json():
    return loudar_dir() / "in" / "in.json"


def out_dir(name):
    return loudar_dir() / "out" / name


def rt_path(name, pk):
    return loudar_dir() / "rt" / name / f"{pk}.npy"


def build_path(rec=False):
    return loudar_dir() / ("build-rec.json" if rec else "build.json")


def figures_path(rec=False):
    return loudar_dir() / ("figures-rec.json" if rec else "figures.json")


def start_path(name, pk):
    return loudar_dir() / "start" / name / f"{pk}.json"


def check_dir():
    return loudar_dir() / "check"


def search_path(name, pk):
    return loudar_dir() / "search" / name / f"{pk}.json"


def answers_path(name):
    return loudar_dir() / f"answers-{name}.json"


def score_path(name, pk):
    return loudar_dir() / "score" / name / f"{pk}.json"


def report_path(rec=False):
    return loudar_dir() / ("report-rec.json" if rec else "report.json")


def rows_path(rec=False):
    return loudar_dir() / ("rows-rec.json" if rec else "rows.json")


def versus_path():
    return loudar_dir() / "versus-notes.json"


# --- the guards ------------------------------------------------------------------------------------------------------------

def loudar_keys(entry):
    return {k: v for k, v in (entry or {}).items() if k.startswith(KEY_PREFIX)}


def code_refusal(main):
    """Why this checkout does not run main's code, or None: CODE_FILES and the `phase_scratch_loudar*` keys equal
    main's; main's blob of learn/scratch_search.py the checked one."""
    from learn import note_replay as NR

    for f in CODE_FILES:
        if SC._git("diff", "--quiet", "origin/main", "--", f).returncode:
            return f"this checkout's {f} differs from main's: run from merged code"
    a, b = loudar_keys(NR.ledger_entry()), loudar_keys(main)
    if a != b:
        return f"this checkout's {sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))} differ from main's"
    return SC.blob_refusal(SC._git("rev-parse", "origin/main:learn/scratch_search.py").stdout.strip())


def require_loudar(*phases):
    fl_table_guard()
    m = S.require_on_main(S.PHASE, S.PHASE_DRAW, SC.GATE, SC.PHASE_OUTCOME, PHASE, *phases)
    why = code_refusal(m)
    if why:
        raise SystemExit(why)
    res = {k: SN.check_result(k) for k in CHECK_SHA256}
    why = SN.checks_passed(res["check-score"], res["check-search"]) or SC.check_refusal(res, SC.check_shas())
    if why:
        raise SystemExit(why)
    return m


def note_rebuild_main():
    """main's note-rebuild entry (for the ear verdict)."""
    from learn import note_transcribe as NT

    led = SC._git("show", "origin/main:docs/dev-test-ledger.json")
    if led.returncode:
        raise SystemExit("main's ledger is not readable")
    return NT.entries(led.stdout).get(NT.LEDGER_ID) or {}


def require_slots():
    from learn import note_transcribe as NT

    why = slots_refusal(SN.report_path().exists(), note_rebuild_main().get(NT.PHASE_EAR))
    if why:
        raise SystemExit(why)


def require_build(m, rec=False):
    from learn import note_replay as NR

    p, phase = build_path(rec), PHASE_DRY_REC if rec else PHASE_DRY
    if not p.exists():
        raise SystemExit(f"no {p.name} (run `build{'-rec' if rec else ''}` first)")
    why = NR.hash_refusal(m, phase, S.file_sha(p))
    if why:
        raise SystemExit(f"{why} (the build's hash must be on main before this step)")
    return json.loads(p.read_text())


def require_name(name, allowed, build=None):
    if name not in allowed:
        raise SystemExit(f"--name {name!r}: one of {list(allowed)}")
    if build is not None and name not in (build.get("names") or {}):
        raise SystemExit(f"{name}: not in the build ({sorted(build.get('names') or {})})")


def require_rec(m):
    """ld-rec's commands: the main read's report reads FL-short or FL-null, and ld-rec's build is hashed."""
    p = report_path()
    why = rec_refusal(json.loads(p.read_text()) if p.exists() else None)
    if why:
        raise SystemExit(why)
    return require_build(m, rec=True)


def build_for(m, name):
    return require_rec(m) if name == REC else require_build(m)


def parts_of(draw, build, name):
    """The parts a name runs on: the build's own list (the 23 deciding; ld-stem also GOAT when it fit)."""
    keys = set((build.get("names") or {}).get(name) or {})
    return [p for p in draw["parts"] if p["pkey"] in keys]


def load_dry(name, pk, build):
    import numpy as np

    x32 = np.load(rt_path(name, pk)).astype(np.float32)
    sha = S.npy_sha(x32)
    want = build["names"][name][pk]["sha256"]
    if sha != want:
        raise SystemExit(f"{pk}: {name}'s dry guitar is not the hashed build's ({sha[:12]}, not {want[:12]})")
    return x32, sha


# --- prep and build (zero renders) -----------------------------------------------------------------------------------------

def cmd_prep(_args):
    """Per part the stem's search half (`note_replay.load_stem("xlnoG", p)[a:b]`, all 47) to in/ld-stem/, and the clean
    record's same span to in/ld-rec/ (the 23); each asserted equal to `scratch_search.load_ref_blank`'s nonzero span
    for the stem. in/in.json: each sha256, each part's half."""
    require_loudar()
    import numpy as np

    from learn import note_replay as NR
    from learn import pipeline_fix as P

    SC.never_overwrite_all([in_json()])
    draw = S.require_draw()
    sd = NR.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    names = {"ld-stem": {"parts": {}}, "ld-rec": {"parts": {}}}
    for p in draw["parts"]:
        k = p["pkey"]
        a, b = half_samples(p["search"])
        stem = np.asarray(NR.load_stem(REF, p), np.float64)
        blank = S.load_ref_blank(sd, p, REF)
        if not np.array_equal(stem[a:b], blank[a:b]) or np.any(blank[:a]) or np.any(blank[b:]):
            raise SystemExit(f"{k}: the clip is not the blanked reference's span")
        clips = {"ld-stem": stem[a:b]}
        if p["set"] in DECIDING:
            prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
            clips["ld-rec"] = np.asarray(P.real_amp_track(prt["sd"], prt["track"], prt["start_s"]), np.float64)[a:b]
        for src, x in clips.items():
            x = np.asarray(x, np.float32)
            if len(x) != CLIP or not np.isfinite(x).all():
                raise SystemExit(f"{k} {src}: {len(x)} samples or non-finite")
            out = in_dir(src) / f"{k}.npy"
            S.never_overwrite(out)
            out.parent.mkdir(parents=True, exist_ok=True)
            np.save(out, x)
            names[src]["parts"][k] = {"sha256": S.file_sha(out), "half": p["search"], "set": p["set"]}
    P.save(in_json(), {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "sr": SR, "n": CLIP,
                       "draw_sha256": S.file_sha(S.draw_path()), "names": names,
                       "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"LOUDAR PREP: ld-stem {len(names['ld-stem']['parts'])} clips, ld-rec {len(names['ld-rec']['parts'])}")


def run_records(name):
    """LOUDAR's run records for a name (out/<name>/run-<name>-<sets>.json), merged by part."""
    recs = sorted(out_dir(name).glob(f"run-{name}-*.json")) if out_dir(name).exists() else []
    parts, files = {}, {}
    for f in recs:
        r = json.loads(f.read_text())
        files[f.name] = {"sha256": S.file_sha(f), "setting": r["setting"], "sets": r["sets"],
                         "seconds_a_clip": r["seconds_a_clip"]}
        parts.update(r["parts"])
    return parts, files


def build_names(draw, sd, names, rec=False):
    """The measured, placed dry guitars and every check, written nothing. -> (held arrays, records, figures,
    timing offsets, LUFS values)."""
    import numpy as np

    from learn import note_replay as NR
    from learn import pretrain_set as PS
    from learn import song_bank as SB

    in_rec = json.loads(in_json().read_text())
    held, recs, figs, offsets, lufs = {}, {n: {} for n in names}, {}, {n: {} for n in names if n in PLACED}, \
        {n: {} for n in names}
    import pyloudnorm

    from learn import direc_check as DC

    meter = pyloudnorm.Meter(DC.SR)
    runs = {n: run_records(n)[0] for n in names if n in SOURCES}
    for p in draw["parts"]:
        k = p["pkey"]
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        di = np.asarray(NR.di_section(prt), np.float64)
        lo, hi, c0, c1 = span(p)
        raw = np.asarray(PS.section_audio(prt["di_path"], prt["start_s"]), np.float64)
        pf = {}
        for n in names:
            if n in SOURCES:
                if k not in runs[n]:
                    continue
                f = out_dir(n) / f"{k}.npy"
                if S.file_sha(f) != runs[n][k]["sha256"]:
                    raise SystemExit(f"{f}: not the file LOUDAR's run wrote")
                clip_raw = np.load(f).astype(np.float64)
            elif n == "stem-in":
                if p["set"] not in DECIDING:
                    continue
                f = in_dir("ld-stem") / f"{k}.npy"
                if S.file_sha(f) != in_rec["names"]["ld-stem"]["parts"][k]["sha256"]:
                    raise SystemExit(f"{f}: not the file prep wrote")
                clip_raw = np.load(f).astype(np.float64)
            else:                                            # di-cut: the raw section cut first, then measured
                if p["set"] not in DECIDING:
                    continue
                clip_raw = raw[lo:hi]
            if not np.isfinite(clip_raw).all():
                raise SystemExit(f"{n} {k}: a non-finite clip")
            meas = SB.measure(clip_raw).astype(np.float32)
            lufs[n][k] = float(meter.integrated_loudness(np.asarray(meas, np.float64)))
            if n == "di-cut":
                y = np.zeros(SECTION, np.float32)
                y[lo:hi] = meas
                if np.any(y[:lo]) or np.any(y[hi:]):
                    raise SystemExit(f"{k}: di-cut is not zero outside its span")
            else:
                if len(meas) != CLIP:
                    raise SystemExit(f"{n} {k}: {len(meas)} samples, not {CLIP}")
                y = place(meas, p)
            if len(y) != SECTION or not np.isfinite(y).all():
                raise SystemExit(f"{n} {k}: not finite or not {SECTION} samples")
            held[(n, k)] = y
            recs[n][k] = {"sha256": S.npy_sha(y), "lufs": lufs[n][k], "span": [lo, hi, c0, c1], "set": p["set"]}
            yi, di_in = np.asarray(y[lo:hi], np.float64), di[lo:hi]
            pf[n] = {"vs_true": SC.dry_figures(di_in, yi), "lufs": lufs[n][k]}
            if n != "di-cut":
                pf[n]["before_measure"] = SC.spectral_distance(raw[lo:hi], clip_raw[c0:c1])
            if n in PLACED:
                offsets[n][k] = SC.envelope_lag_ms(di_in, yi)
                pf[n]["lag_ms"], pf[n]["lag_samples"] = offsets[n][k], SC.waveform_lag(di_in, yi)
        figs[k] = pf
    return held, recs, figs, offsets, lufs


def timing_stop(offsets, sets_of, tol=TIMING_MS, stop=TIMING_STOP):
    """(Pure.) The codec row's rule as a check, never a correction: {name: {pkey: lag ms}} -> ({name: [deciding pkeys
    beyond tol]}, stopped when any name has `stop` or more deciding parts beyond)."""
    beyond = {n: sorted(k for k, v in d.items() if sets_of.get(k) in DECIDING and (v is None or abs(v) > tol))
              for n, d in offsets.items()}
    return beyond, any(len(v) >= stop for v in beyond.values())


def write_build(draw, rec, held, recs, figs, offsets, lufs, names):
    import numpy as np

    from learn import pipeline_fix as P

    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    beyond, tstop = timing_stop(offsets, sets_of)
    off_level = SC.lufs_beyond(lufs)
    runs = {n: run_records(n)[1] for n in names if n in SOURCES}
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "draw_sha256": S.file_sha(S.draw_path()),
           "in_json_sha256": S.file_sha(in_json()), "run_records": runs,
           "settings": sorted({r["setting"] for v in runs.values() for r in v.values()}),
           "lufs_beyond": off_level, "timing_beyond_1ms": beyond, "timing_stopped": tstop,
           "goat_built": any(sets_of[k] == "goat" for k in recs.get("ld-stem", {})),
           "time": time.strftime("%Y-%m-%d %H:%M:%S"), "names": recs}
    if len(out["settings"]) > 1:
        raise SystemExit(f"LOUDAR's runs used more than one setting: {out['settings']}")
    why = []
    if off_level:
        why.append(f"{len(off_level)} measured clips more than {SC.LUFS_TOL} LU off {SC.LUFS}")
    if tstop:
        why.append(f"the timing check: {beyond} (3 or more deciding parts beyond 1 ms): stop and ask before renders")
    if why:
        P.save(loudar_dir() / f"build{'-rec' if rec else ''}-stopped-{time.strftime('%Y%m%d-%H%M%S')}.json",
               dict(out, stopped=why))
        raise SystemExit("the build stops: " + "; ".join(why))
    for (n, k), y in held.items():
        f = rt_path(n, k)
        S.never_overwrite(f)
        f.parent.mkdir(parents=True, exist_ok=True)
        np.save(f, y)
        if S.file_sha(f) != recs[n][k]["sha256"]:
            raise SystemExit(f"{f}: the file's sha256 is not npy_sha's")
    P.save(figures_path(rec), {"plan": PLAN, "parts": figs, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    out["figures_sha256"] = S.file_sha(figures_path(rec))
    P.save(build_path(rec), out)
    print(f"LOUDAR BUILD{' REC' if rec else ''}: {', '.join(f'{n} {len(v)}' for n, v in recs.items())}; timing beyond "
          f"1 ms {beyond}; sha256 {S.file_sha(build_path(rec))} (into the ledger as "
          f"{PHASE_DRY_REC if rec else PHASE_DRY} before any render)")


def cmd_build(_args):
    """`ld-stem` (and `ld-stem-b` where LOUDAR ran it), `stem-in` and `di-cut`: each measured on its clip and placed;
    every check (LUFS, finite, lengths, di-cut zero outside its span, the timing check) before anything is written.
    -> rt/, figures.json, build.json (its sha256 for phase_scratch_loudar_dry)."""
    require_loudar()
    from learn import note_replay as NR

    SC.never_overwrite_all([build_path(), figures_path()])
    draw = S.require_draw()
    sd = NR.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    if not run_records("ld-stem")[0]:
        raise SystemExit("no LOUDAR run for ld-stem")
    names = [n for n in ("ld-stem", "ld-stem-b") if run_records(n)[0]] + ["stem-in", "di-cut"]
    write_build(draw, False, *build_names(draw, sd, names), names)


def cmd_build_rec(_args):
    """ld-rec's build, only after FL-short or FL-null: as `build`, for ld-rec alone. -> build-rec.json (its sha256
    for phase_scratch_loudar_dry_rec)."""
    m = require_loudar(PHASE_DRY)
    p = report_path()
    why = rec_refusal(json.loads(p.read_text()) if p.exists() else None)
    if why:
        raise SystemExit(why)
    from learn import note_replay as NR

    SC.never_overwrite_all([build_path(True), figures_path(True)])
    require_build(m)
    draw = S.require_draw()
    sd = NR.Stored()
    write_build(draw, True, *build_names(draw, sd, [REC], rec=True), [REC])


# --- the start reads, the control, the short rows (renders) ---------------------------------------------------------------

def cmd_start(args):
    """The start reads (2 renders a part): `scratch_codec.start_value` for the name's parts."""
    m = require_loudar(PHASE_DRY)
    build = build_for(m, args.name)
    require_name(args.name, NAMES, build)
    require_slots()
    from learn import cc_build as CB
    from learn import note_replay as NR

    draw = S.require_draw()
    sd = NR.Stored()
    SC.render_guards(draw, sd)
    total = 0
    for p in SC.shard_of(parts_of(draw, build, args.name), args.shard):
        if start_path(args.name, p["pkey"]).exists():
            continue
        SC.disk_guard()
        x32, sha = load_dry(args.name, p["pkey"], build)
        _, used = SC.start_value(p, args.name, x32, S.load_ref_blank(sd, p, REF), CB.new_renderer,
                                 start_path(args.name, p["pkey"]), sha)
        total += used
    print(f"LOUDAR START DONE {args.name} {args.shard[0]}/{args.shard[1]}: {total} renders")


def cmd_control(_args):
    """The control (22 renders), once: `di-whole` (the true DI, uncut) on the 2 check parts through this module's
    search path (`scratch_codec.short_search`) at a budget of 10, against row (b)'s stored records."""
    m = require_loudar(PHASE_DRY)
    require_build(m)
    require_slots()
    S.never_overwrite(check_dir() / "result.json")
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import note_replay as NR
    from learn import pipeline_fix as P

    draw = S.require_draw()
    sd = NR.Stored()
    SC.render_guards(draw, sd)
    by = {p["pkey"]: p for p in draw["parts"]}
    lists = C.mic_lists()
    new, stored, total = {}, {}, 0
    for k in SN.check_parts(draw["parts"]):
        p = by[k]
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        x32 = NR.di_section(prt)
        out = check_dir() / f"{k}.json"
        S.never_overwrite(out)
        rec = SC.short_search(p, CONTROL_NAME, x32, S.npy_sha(x32), S.load_ref_blank(sd, p, REF), CB.new_renderer,
                              lists, p["start_ref"]["true"][REF], budget=SC.CONTROL_BUDGET)
        total += rec.get("renders", 0)
        P.save(out, rec)
        new[k], stored[k] = rec, json.loads(S.search_path(SC.STEM_ROW, k).read_text())
    verdict = SN.search_check_verdict(new, stored)
    P.save(check_dir() / "result.json", {"plan": PLAN, "renders": total, "budget": SC.CONTROL_BUDGET,
                                         "search": verdict, "passed": verdict["passed"],
                                         "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"LOUDAR CONTROL {'PASS' if verdict['passed'] else 'FAIL'}: {total} renders; {verdict['mismatches']}")


def require_control():
    p = check_dir() / "result.json"
    why = SC.control_refusal(json.loads(p.read_text()) if p.exists() else None)
    if why:
        raise SystemExit(why)


def cmd_search(args):
    """One shard of a name's short searches (51 renders a part), the hashed dry guitar, `scratch_codec.short_search`."""
    m = require_loudar(PHASE_DRY)
    build = build_for(m, args.name)
    require_name(args.name, SEARCHED + (REC,), build)
    require_slots()
    require_control()
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import note_replay as NR
    from learn import pipeline_fix as P

    draw = S.require_draw()
    sd = NR.Stored()
    SC.render_guards(draw, sd)
    mine = SC.shard_of(parts_of(draw, build, args.name), args.shard)
    if args.first:
        mine = mine[:args.first]
    lists = C.mic_lists()
    total, t0 = 0, time.time()
    for p in mine:
        out = search_path(args.name, p["pkey"])
        if out.exists():
            continue
        SC.disk_guard()
        x32, sha = load_dry(args.name, p["pkey"], build)
        sp = start_path(args.name, p["pkey"])
        if not sp.exists() or json.loads(sp.read_text())["dry_sha256"] != sha:
            raise SystemExit(f"{p['pkey']}: no {args.name} start value for this dry guitar (run `start` first)")
        rec = SC.short_search(p, args.name, x32, sha, S.load_ref_blank(sd, p, REF), CB.new_renderer, lists,
                              json.loads(sp.read_text())["value"])
        rec["ledger"] = f"{LEDGER_ID} {PHASE}"
        S.never_overwrite(out)
        P.save(out, rec)
        total += rec.get("renders", 0)
    print(f"FS-LOUDAR SEARCH DONE {args.name} {args.shard[0]}/{args.shard[1]}: {total} renders in "
          f"{time.time() - t0:.0f} s")


def cmd_answers(args):
    """A name's short answers (zero renders): `scratch_codec.short_answers`; the refusal stop on the 23 deciding parts.
    -> answers-<name>.json; its sha256 into the ledger as the name's answers key."""
    m = require_loudar(PHASE_DRY)
    build = build_for(m, args.name)
    require_name(args.name, SEARCHED + (REC,), build)
    S.never_overwrite(answers_path(args.name))
    from learn import pipeline_fix as P

    draw = S.require_draw()
    parts = parts_of(draw, build, args.name)
    recs = {}
    for p in parts:
        sp = search_path(args.name, p["pkey"])
        if not sp.exists():
            raise SystemExit(f"{p['pkey']}: not searched")
        recs[p["pkey"]] = json.loads(sp.read_text())
    shas = {k: v["sha256"] for k, v in build["names"][args.name].items()}
    ans, refused, _ = SC.short_answers(parts, recs, shas, lambda k: S.file_sha(search_path(args.name, k)))
    dec, beside, stop = deciding_stop(refused, {p["pkey"]: p["set"] for p in parts})
    out = {"plan": PLAN, "row": ROW, "dry": args.name, "ref": S.REF_NAME[REF], "checkpoint": SC.CHECKPOINT,
           "draw_sha256": S.file_sha(S.draw_path()), "build_sha256": S.file_sha(build_path(args.name == REC)),
           "renders": sum(r.get("renders", 0) for r in recs.values()), "refused": refused,
           "refused_deciding": dec, "refused_beside": beside, "stopped": stop, "parts": ans,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(answers_path(args.name), out)
    print(f"FS-LOUDAR ANSWERS {args.name}: {len(ans)} parts, {len(refused)} refused ({len(dec)} deciding"
          f"{', STOPPED' if stop else ''}); sha256 {S.file_sha(answers_path(args.name))} (into the ledger as "
          f"{phase_answers(args.name)} before `score`)")


def require_answers(m, name):
    from learn import note_replay as NR

    p = answers_path(name)
    if not p.exists():
        raise SystemExit(f"no answers for {name}")
    why = NR.hash_refusal(m, phase_answers(name), S.file_sha(p))
    if why:
        raise SystemExit(f"{why} (the hash must be on main before this step)")
    return json.loads(p.read_text())


def cmd_score(args):
    """One shard of a name's score (4 renders a part): `scratch_search.score_row_part` on the hashed answers."""
    require_name(args.name, SEARCHED + (REC,))
    m = require_loudar(PHASE_DRY, phase_answers(args.name))
    build_for(m, args.name)
    require_slots()
    ans = require_answers(m, args.name)
    if ans["stopped"]:
        raise SystemExit(f"{args.name} stopped at the refusal count: nothing is scored")
    from learn import cc_build as CB
    from learn import note_replay as NR
    from learn import pipeline_fix as P

    draw = S.require_draw()
    sd = NR.Stored()
    SC.render_guards(draw, sd)
    sha = S.file_sha(answers_path(args.name))
    total = 0
    for p in SC.shard_of([q for q in draw["parts"] if q["pkey"] in ans["parts"]], args.shard):
        out = score_path(args.name, p["pkey"])
        if out.exists():
            continue
        SC.disk_guard()
        rec, used = S.score_row_part(p, ans["parts"][p["pkey"]], ans["parts"], ROW, sha, sd, CB.new_renderer)
        total += used
        P.save(out, rec)
    print(f"FS-LOUDAR SCORE DONE {args.name} {args.shard[0]}/{args.shard[1]}: {total} renders")


# --- the read (zero renders) -----------------------------------------------------------------------------------------------

def bp_rows(sd, draw, values):
    """`note_replay.summary`'s set rows for BKS, the panel and GOAT, and BKS+panel pooled by
    `full_controls_c3r.pooled` (equal weights). values: {pkey: value}. -> {"bp", "bks", "panel", "goat", "row"}."""
    from learn import full_controls_c3r as R
    from learn import note_replay as NR

    parts = [dict(p, cluster=p["cluster"].split("|", 1)[1]) for p in draw["parts"] if values.get(p["pkey"]) is not None]
    if not parts:
        return None
    row = NR.summary(sd.units, parts, values, NR.lender_band())
    sets = {s: row.get(s) or {} for s in DECIDING}
    bp = R.pooled(sets) if all(v.get("mean") is not None for v in sets.values()) else None
    return {"bp": bp, "bks": row.get("bks"), "panel": row.get("panel"), "goat": row.get("goat"),
            "leave_one_cluster_out": row.get("leave_one_cluster_out"), "row": row}


def g50_of(draw, name, m):
    """A name's per-part G50 from its hashed answers and score files (`scratch_codec.codec_g50`)."""
    ans = require_answers(m, name)
    return SC.codec_g50(draw, ans, S.file_sha(answers_path(name)), lambda k: score_path(name, k))


def numbers(g, comp, gcut=None, gin=None):
    """(Pure.) The per-part numbers: D_blur, D_true, D_cut, D_bar, D_null (paired where both exist)."""
    gb, gc = comp["fs-stem"], comp["fs-both"]
    out = {"D_blur": SC.paired(g, gc), "D_true": SC.paired(g, gb)}
    if gcut is not None:
        out["D_cut"] = SC.paired(gcut, gb)
        out["D_bar"] = SC.paired(out["D_blur"], out["D_cut"])
    if gin is not None:
        out["D_null"] = SC.paired(g, gin)
    return out


def read_body(sd, draw, m, name, gin=None):
    """The rows of a read for `name` (ld-stem or ld-rec): G50, the five numbers, rows (b) and (c), rt-m2l."""
    comp_full = SC.comparators()
    comp = {r: comp_full[r][0] for r in comp_full}
    per, refused, replaced, miss = g50_of(draw, name, m)
    g = {k: v for k, v in per.items() if v is not None}
    gcut = {k: v for k, v in g50_of(draw, "di-cut", m)[0].items() if v is not None}
    if gin is None:
        gin = {k: v for k, v in g50_of(draw, "stem-in", m)[0].items() if v is not None}
    nums = numbers(g, comp, gcut, gin)
    ans_m2l = SC.require_answers(m, "rt-m2l")
    gm2l = SC.codec_g50(draw, ans_m2l, S.file_sha(SC.answers_path("rt-m2l")), lambda k: SC.score_path("rt-m2l", k))[0]
    rows = {q: bp_rows(sd, draw, v) for q, v in nums.items()}
    rows["G50"] = bp_rows(sd, draw, g)
    rows["G50_stem_in"] = bp_rows(sd, draw, gin)
    rows["G50_di_cut"] = bp_rows(sd, draw, gcut)
    rows["G50_rows_b_c"] = {r: bp_rows(sd, draw, v) for r, v in comp.items()}
    rows["vs_codec_ceiling"] = bp_rows(sd, draw, SC.paired(g, {k: v for k, v in gm2l.items() if v is not None}))
    room = (rows["D_true"]["bp"] or {}).get("mean"), bp_rows(sd, draw, SC.paired(comp["fs-both"], comp["fs-stem"]))
    rows["room_kept"] = (1 - room[0] / room[1]["bp"]["mean"]) if room[0] is not None and room[1] and \
        room[1]["bp"] and room[1]["bp"]["mean"] else None
    rows["parts_at_or_over_0.10"] = sorted(k for k, v in g.items() if v >= BIG)
    head = {"refused": refused, "nonfinite_replaced": replaced, "scoring_control_misses": miss}
    return rows, head, g


def cmd_read(_args):
    """The row's read (zero renders), once: G50 of ld-stem, di-cut, stem-in; D_blur, D_true, D_cut, D_bar, D_null on
    BKS+panel (`bp_rows`); the pool rule; the rows saved before `fl_code`; GOAT beside (in-sample for the prior).
    -> rows.json, report.json (`next: "ld-rec"` on FL-short or FL-null)."""
    m = require_loudar(PHASE_DRY, *(phase_answers(n) for n in SEARCHED))
    build = require_build(m)
    SC.never_overwrite_all([rows_path(), report_path()])
    from learn import note_replay as NR
    from learn import pipeline_fix as P

    draw = S.require_draw()
    sd = NR.Stored()
    rows, head, g = read_body(sd, draw, m, "ld-stem")
    out = {"plan": PLAN, "row": ROW, **head, "goat_built": build.get("goat_built"),
           "answers_sha256": {n: S.file_sha(answers_path(n)) for n in SEARCHED},
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(rows_path(), dict(out, rows=rows))                # the rows are saved before the code is read
    for q in ("G50", "D_blur", "D_null", "D_cut", "D_bar"):
        why = pool_refusal(rows[q] or {})
        if why:
            P.save(report_path(), dict(out, rows=rows, fl=None, stopped=True, stop_reason=f"{q}: {why}"))
            raise SystemExit(f"{q}: {why}; to the user")
    fl = fl_code(rows["D_null"]["bp"], rows["D_blur"]["bp"], rows["D_cut"]["bp"], rows["D_bar"]["bp"],
                 rows["G50"]["bp"], rows["G50_rows_b_c"]["fs-both"]["bp"])
    goat = goat_reading((rows["D_blur"]["goat"] or None) if build.get("goat_built") else None)
    rep = dict(out, rows=rows, fl=fl, goat=goat, next="ld-rec" if fl["code"] in REC_CODES else fl["next"],
               bks_g50_below_zero=((rows["G50"]["bks"] or {}).get("hi90") or 0) < 0)
    if SN.report_path().exists():
        rep["versus_notes"] = "run `versus-notes` (zero renders, once)"
    P.save(report_path(), rep)
    d = rows[fl["number"]]["bp"]
    print(f"fs-loudar: {fl['number']} {d['mean']:+.3f} [{d['lo90']:+.3f}, {d['hi90']:+.3f}] on BKS+panel -> "
          f"{fl['code']}: {fl['reading']}. Next: {rep['next']}")


def cmd_read_rec(_args):
    """ld-rec's read (zero renders), once, after its row: the same table on ld-rec, then `bottleneck`."""
    m = require_loudar(PHASE_DRY, PHASE_DRY_REC, phase_answers(REC), *(phase_answers(n) for n in SEARCHED))
    require_rec(m)
    SC.never_overwrite_all([rows_path(True), report_path(True)])
    from learn import note_replay as NR
    from learn import pipeline_fix as P

    draw = S.require_draw()
    sd = NR.Stored()
    main_rep = json.loads(report_path().read_text())
    rows, head, _ = read_body(sd, draw, m, REC)
    out = {"plan": PLAN, "row": ROW + " (ld-rec)", **head, "answers_sha256": S.file_sha(answers_path(REC)),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(rows_path(True), dict(out, rows=rows))
    fl = fl_code(rows["D_null"]["bp"], rows["D_blur"]["bp"], rows["D_cut"]["bp"], rows["D_bar"]["bp"],
                 rows["G50"]["bp"], rows["G50_rows_b_c"]["fs-both"]["bp"])
    bn = bottleneck(fl["code"], main_rep.get("goat"))
    P.save(report_path(True), dict(out, rows=rows, fl=fl, bottleneck=bn))
    print(f"ld-rec: {fl['code']}; bottleneck: {bn['bottleneck']}")


def cmd_versus_notes(_args):
    """Zero renders, once, after both rows are read: G50(ld-stem) less fs-notes' G50 at the checkpoint, and less
    fs-notes' best arm (answer or shrunk, the lower mean on BKS, said to have had 212 more renders a part), on BKS
    first (the only set clean for both: 16 parts from 2 songs) and BKS+panel beside."""
    m = require_loudar(PHASE_DRY, *(phase_answers(n) for n in SEARCHED))
    S.never_overwrite(versus_path())
    if not report_path().exists() or not SN.report_path().exists():
        raise SystemExit("both rows must be read first (report.json here and fs-notes')")
    from learn import note_replay as NR
    from learn import pipeline_fix as P

    draw = S.require_draw()
    sd = NR.Stored()
    sha = S.file_sha(SN.answers_path())
    why = NR.hash_refusal(m, SN.PHASE_ANSWERS, sha)
    if why:
        raise SystemExit(why)
    rby = {p["pkey"]: p for p in NR.require_draw()["parts"]}
    per_n = S.read_row_parts(draw, json.loads(SN.answers_path().read_text()), sha, SN.score_path, sd, rby)[0]
    g = {k: v for k, v in g50_of(draw, "ld-stem", m)[0].items() if v is not None}
    arms = {"G_cp50": "checkpoint", "G": "answer", "G_shrunk": "shrunk"}
    res = {}
    for f in arms:
        other = {k: v[f] for k, v in per_n.items() if v and v.get(f) is not None}
        res[arms[f]] = bp_rows(sd, draw, SC.paired(g, other))
    means = {a: ((bp_rows(sd, draw, {k: v[f] for k, v in per_n.items() if v and v.get(f) is not None}) or {})
                 .get("bks") or {}).get("mean") for f, a in arms.items() if a != "checkpoint"}
    best = SC.best_arm(means)
    P.save(versus_path(), {"plan": PLAN, "width_bks": notes_width(draw["parts"]), "best_arm": best, "rows": res,
                           "note": "fs-notes reads its notes from the true DI; ld-stem hears only the stem. The best "
                                   "arm had 212 more renders a part", "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    c = (res["checkpoint"] or {}).get("bks") or {}
    print(f"versus fs-notes on BKS (checkpoint): {c.get('mean')} [{c.get('lo90')}, {c.get('hi90')}]; best arm {best}")


# --- main ------------------------------------------------------------------------------------------------------------------

COMMANDS = {"prep": cmd_prep, "build": cmd_build, "build-rec": cmd_build_rec, "start": cmd_start,
            "control": cmd_control, "search": cmd_search, "answers": cmd_answers, "score": cmd_score,
            "read": cmd_read, "read-rec": cmd_read_rec, "versus-notes": cmd_versus_notes}
NEEDS_NAME = ("start", "search", "answers", "score")
RENDER_COMMANDS = ("start", "control", "search", "score")


def main(argv=None):
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    for p_ in (str(root), str(root / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--name", choices=NAMES)
    ap.add_argument("--shard", type=S._shard, default=(0, 1))
    ap.add_argument("--first", type=int, default=0)
    args = ap.parse_args(argv)
    if args.cmd in NEEDS_NAME and not args.name:
        ap.error(f"{args.cmd} needs --name")
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
