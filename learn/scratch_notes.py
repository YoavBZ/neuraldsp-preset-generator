"""The from-scratch search's `fs-notes` row: the search driven by the note rebuild's `tr-di`, the guitar re-played from
single recorded notes at notes Basic Pitch read from the DI (`docs/scratch-search-plan.md` section 10,
`docs/note-rebuild-plan.md` section 12; ledger `preset-ladder` `phase_scratch_notes`, then `phase_scratch_notes_dry`,
`phase_scratch_notes_answers`, `phase_scratch_notes_outcome`).

`fs-notes` = (`tr-di`, `xlnoG`): `tr-di` is the dry guitar of every search render and the judge's DI; the search-half
reference is `xlnoG@-3`; the answers are rendered through the true DI and judged on the held half against the clean
record. Same draw, Cen, partners, budget, seeds, checkpoints and halves as rows (b) and (c), through the same code:
`scratch_search.search_row_part`, `answer_parts`, `score_row_part` and `read_row_parts` (the refactor of PR 1; rows
(b) and (c) run through them unchanged).

    $MAIN -m learn.scratch_notes score-check       # step 4: two parts of row (c) re-scored (about 40 renders)
    $MAIN -m learn.scratch_notes search-check      # step 4: two parts' first 10 evaluations (about 24 renders)
    $MAIN -m learn.scratch_notes search --shard 0/3 [--first 2]    # step 9: renders; at most 3 shards
    $MAIN -m learn.scratch_notes answers           # step 10 (zero renders): its sha256 -> phase_scratch_notes_answers
    $MAIN -m learn.scratch_notes score --shard 0/3 # step 11: the only step that reads a held half
    $MAIN -m learn.scratch_notes read              # step 11 (zero renders): D_notes, FN_TABLE's code, once

Every command refuses unless this checkout runs main's redo (`note_transcribe.redo_on_main`) and main's ledger holds
`phase_scratch_notes`, `phase_scratch_both_outcome` and `phase_nr_1_redo`. `search` refuses until both checks have
passed and the build is hashed (`phase_scratch_notes_dry`); `answers` refuses a search record whose dry guitar's
sha256 is not the hashed build's; `answers`, `score` and `read` refuse without `phase_nr_1_redo_ear` = ok.

The pure parts (`paired_reading`, `FN_TABLE`, `fn_code` and its guard, the lean recommendations, the bottleneck rule,
the checks' verdicts, the refusal stop on the 40, every refusal) are tested in tests/test_scratch_notes.py on the light
CI runner (no numpy).
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import time

from learn import note_transcribe as NT
from learn import scratch_search as S

LEDGER_ID = S.LEDGER_ID                  # preset-ladder
PLAN = "docs/scratch-search-plan.md"
PHASE = "phase_scratch_notes"            # this declaration
PHASE_DRY = NT.PHASE_DRY                 # the redo build's sha256 (phase_scratch_notes_dry)
PHASE_ANSWERS = "phase_scratch_notes_answers"
PHASE_OUTCOME = "phase_scratch_notes_outcome"
GATE = "phase_scratch_both_outcome"      # row (c)'s audited F-both on main
ROW = "fs-notes"
BUILD_NAME = None                        # a later build's name (`--build-name`): its own dry key, record and folders
DRY, REF = "tr-di", "xlnoG"
COMPARATOR = "fs-both"                   # row (c): D_notes = G(fs-notes) - G(fs-both), per part
STEM_ROW = "fs-stem"                     # row (b): the share of its gain kept (beside)
ARMS = {"answer": "G", "shrunk": "G_shrunk"}   # both always scored; the same arm throughout a row of FN_TABLE
DECIDING = NT.DECIDING                   # BKS+GOAT (40 parts): the user's exception for this row only
CLASSES = ("clean", "crunch")
SUBSETS = ("all",) + CLASSES             # "all": the 40
SMALL, BIG = S.SMALL, S.BIG              # 0.05, 0.10 (the user's rule)
CHECK_BUDGET = 10                        # the search check's step-1 budget
CHECK_SETS = ("bks", "goat")             # the checks' parts: the first BKS and the first GOAT part by key


# --- the paired reading and the decision table (pure) ----------------------------------------------------------------------

def paired_reading(iv, small=SMALL, big=BIG):
    """(Pure.) `D_notes` on a set: "better" (the whole 90% interval below zero, the mean at -big or beyond); "matches"
    (the upper end under +big, a heard-size loss ruled out, and the mean under +small); "worse" (the whole interval
    above zero, the mean at +big or beyond); "undecided" otherwise. An interval inside +-small is worded "level, not
    readable by the score". -> {reading, level_not_readable} or None without an interval."""
    if not iv or any(iv.get(k) is None for k in ("mean", "lo90", "hi90")):
        return None
    m, lo, hi = iv["mean"], iv["lo90"], iv["hi90"]
    if hi < 0 and m <= -big:
        r = "better"
    elif hi < big and m < small:
        r = "matches"
    elif lo > 0 and m >= big:
        r = "worse"
    else:
        r = "undecided"
    return {"reading": r, "level_not_readable": lo >= -small and hi <= small}


def _r(x):
    return (x or {}).get("reading")


FN_TABLE = (    # (code, when on BKS+GOAT (the first that holds; "an arm" is the same arm throughout), reading)
    ("FN-match", "an arm matches or is better on the 40 and on the clean 20, its own G on the 40 has its upper end "
     "below zero, and its own G on clean does not read fails",
     "with these notes the rebuilt guitar drives the search as well as the blurred true DI, clean included, and the "
     "row itself beats Cen"),
    ("FN-crunch", "not the above; an arm matches or is better on the crunch 20, and its own G on crunch has its upper "
     "end below zero", "it holds on crunch; clean is worded from its own reading"),
    ("FN-worse", "both arms read worse on the 40", "it fails with the current transcriber and synthesis; not a verdict "
     "on the note route"),
    ("FN-clean-worse", "both arms read worse on the clean 20", "clean fails with the current parts; the 40 and crunch "
     "are not decided"),
    ("FN-undecided", "anything else", "not decided; undecided is not failed"),
)
FN_CODES = tuple(c for c, *_ in FN_TABLE)
FN_LICENCE = {   # what each licenses, and the recommendation (declared now; every line goes to the user)
    "FN-match": "the stem-notes row, under its own declaration; then a blind sitting that includes the losing parts. "
                "The flagged build stays held",
    "FN-crunch": "recommend the stem-notes row, and that its declaration ask the user for crunch to decide with clean "
                 "read beside. Where clean read worse: clean leaves the note route with the current parts and keeps "
                 "today's start; the bottleneck is named. No clean claim",
    "FN-worse": "no stem-notes row. To the user, with the bottleneck named and one recommendation: fix that part, or "
                "the declared fallbacks (guided or network route). Audited adversarially first",
    "FN-clean-worse": "as FN-worse for clean. For crunch, FN-undecided's rule on the crunch 20",
    "FN-undecided": "two recommendations, not codes: lean-go (the stem-notes row, read against row (c)'s bar directly; "
                    "a heard-size loss against avg+mild is not ruled out, and the split is a cut on the point estimate "
                    "of an undecided interval) or lean-stop (worded \"undecided, recommend no more renders on this "
                    "build\", never \"fails\"; the bottleneck is named)",
}


def matches_or_better(x):
    return _r(x) in ("matches", "better")


def g_below_zero(g):
    return bool(g) and g.get("hi90") is not None and g["hi90"] < 0


def clean_wording(d_clean):
    """(Pure.) FN-crunch's words for clean, from the same arm's clean reading."""
    r = _r(d_clean)
    if r == "worse":
        return "worse"
    if r in ("matches", "better"):
        return "matches, but the row does not beat Cen there"
    return "undecided"


def lean(arms, subset="all", small=SMALL):
    """(Pure.) FN-undecided's recommendation on `subset`: "lean-go" when some arm's mean D_notes is under +small and its
    own G there has its upper end below zero; else "lean-stop". -> (recommendation, arm or None)."""
    for arm in ARMS:
        d = arms[arm]["D"].get(subset) or {}
        if d.get("mean") is not None and d["mean"] < small and g_below_zero(arms[arm]["G"].get(subset)):
            return "lean-go", arm
    return "lean-stop", None


def fn_code(arms):
    """(Pure.) FN_TABLE's code: the first row that holds. arms: {arm: {"D": {subset: paired_reading's input row (mean,
    lo90, hi90) with its "reading"}, "G": {subset: the arm's own G row}}} for both ARMS, subsets "all" (the 40),
    "clean", "crunch". -> {code, arm, reading, licence, clean (FN-crunch), lean (FN-undecided, FN-clean-worse)}."""
    rd = {a: {s: paired_reading(arms[a]["D"].get(s)) for s in SUBSETS} for a in ARMS}
    out = None
    for a in ARMS:
        g = arms[a]["G"]
        if (matches_or_better(rd[a]["all"]) and matches_or_better(rd[a]["clean"]) and g_below_zero(g.get("all"))
                and S.number_reading(g.get("clean")) != "fails"):
            out = {"code": "FN-match", "arm": a}
            break
    if out is None:
        for a in ARMS:
            if matches_or_better(rd[a]["crunch"]) and g_below_zero(arms[a]["G"].get("crunch")):
                out = {"code": "FN-crunch", "arm": a, "clean": clean_wording(rd[a]["clean"])}
                break
    if out is None and all(_r(rd[a]["all"]) == "worse" for a in ARMS):
        out = {"code": "FN-worse", "arm": None}
    if out is None and all(_r(rd[a]["clean"]) == "worse" for a in ARMS):
        out = {"code": "FN-clean-worse", "arm": None, "lean": lean(arms, "crunch")}
    if out is None:
        out = {"code": "FN-undecided", "arm": None, "lean": lean(arms, "all")}
    text = {c: r for c, _, r in FN_TABLE}
    return {**out, "reading": text[out["code"]], "licence": FN_LICENCE[out["code"]], "readings": rd}


def fn_table_guard():
    """Refuse unless FN_TABLE holds the five declared codes in order, each with its licence, and 0 < SMALL < BIG."""
    if FN_CODES != ("FN-match", "FN-crunch", "FN-worse", "FN-clean-worse", "FN-undecided"):
        raise SystemExit("FN_TABLE's codes are not the five declared, in order")
    if set(FN_LICENCE) != set(FN_CODES):
        raise SystemExit("a code has no declared licence")
    if not 0 < SMALL < BIG:
        raise SystemExit("the thresholds are not 0 < SMALL < BIG")


# --- the bottleneck, the split and the checks (pure) -----------------------------------------------------------------------

def median_split(values):
    """(Pure.) The parts split at the median of a figure: (lower half, upper half) of pkeys, sorted by (value, pkey);
    an odd middle goes to the upper half; parts without the figure are left out. values: {pkey: value or None}."""
    ks = sorted((k for k, v in values.items() if v is not None), key=lambda k: (values[k], k))
    return ks[:len(ks) // 2], ks[len(ks) // 2:]


def diff_interval(lower, upper):
    """(Pure.) lower's mean less upper's, with a 90% interval from the two halves' half-widths combined in quadrature
    (a declared approximation: the halves are disjoint parts). -> {mean, lo90, hi90} or None."""
    if not lower or not upper or any(r.get(k) is None for r in (lower, upper) for k in ("mean", "lo90", "hi90")):
        return None
    d = lower["mean"] - upper["mean"]
    h = math.hypot((lower["hi90"] - lower["lo90"]) / 2, (upper["hi90"] - upper["lo90"]) / 2)
    return {"mean": d, "lo90": d - h, "hi90": d + h}


def bottleneck(upper, lower, big=BIG):
    """(Pure.) Section 10's descriptive split of the 40 at the median of `onsets-found`: "the synthesis" when D_notes'
    mean on the better-transcribed half (`upper`) is at +big or worse with its interval clear of zero; "the
    transcriber" when the lower half's mean is worse than the upper's by big or more with the difference's interval
    clear of zero (`diff_interval`); otherwise "not separable by these figures". -> (names, the difference)."""
    out = []
    if upper and upper.get("mean") is not None and upper["mean"] >= big and (upper.get("lo90") or 0) > 0:
        out.append("the synthesis")
    d = diff_interval(lower, upper)
    if d and d["mean"] >= big and d["lo90"] > 0:
        out.append("the transcriber")
    return (out or ["not separable by these figures"]), d


FIGURES = ("ring_kept_db", "bent_share", "chord_share")   # read beside the bottleneck (plan 5, section 10b)


def part_figures(build_parts, keys):
    """(Pure.) The three figures read beside the bottleneck, per part in `keys`, from the build record: `ring-kept`'s
    late-level median (dB; None where not measured), the share of bent notes and the share of chords (`note_transcribe.
    content_shares`). -> {figure: {pkey: value or None}}."""
    out = {f: {} for f in FIGURES}
    for k in keys:
        r = build_parts.get(k) or {}
        rk = (((r.get("arms") or {}).get(DRY) or {}).get("figures") or {}).get("ring-kept") or {}
        out["ring_kept_db"][k] = rk.get("late_median_db")
        out["bent_share"][k] = r.get("bent_share")
        out["chord_share"][k] = r.get("chord_share")
    return out


def spearman(pairs):
    """(Pure.) Spearman's rho of [(x, y)] (ties at their mean rank), or None under 3 pairs or with no spread."""
    if len(pairs) < 3:
        return None

    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for q in order[i:j + 1]:
                r[q] = (i + j) / 2
            i = j + 1
        return r
    return _pearson(list(zip(ranks([x for x, _ in pairs]), ranks([y for _, y in pairs]))))


def by_figure(d, values):
    """(Pure.) D_notes read by a figure: Spearman's rho over the parts carrying both, and the parts split at the
    figure's median (`median_split`) with each half's mean D_notes. d: {pkey: D_notes}; values: {pkey: figure}."""
    v = {k: values.get(k) for k in d}
    lower, upper = median_split(v)
    mean = (lambda ks: sum(d[k] for k in ks) / len(ks) if ks else None)    # noqa: E731
    return {"parts": len(lower) + len(upper), "spearman": spearman([(v[k], d[k]) for k in lower + upper]),
            "lower": lower, "upper": upper, "lower_mean": mean(lower), "upper_mean": mean(upper)}


def share_of(row, ref):
    """(Pure.) row's mean over ref's (the share of row (b)'s gain kept), or None when either is missing or ref is 0."""
    if not row or not ref or row.get("mean") is None or not ref.get("mean"):
        return None
    return row["mean"] / ref["mean"]


def check_parts(parts):
    """(Pure.) The checks' two parts: the first BKS and the first GOAT part by key."""
    return [sorted(p["pkey"] for p in parts if p["set"] == s)[0] for s in CHECK_SETS]


def score_check_verdict(new, stored):
    """(Pure.) score-check: every setting's held value and render sha256 equal the stored file's, the same settings.
    new, stored: {pkey: score record}. -> {passed, mismatches}."""
    bad = []
    for k in sorted(stored):
        a, b = new.get(k) or {}, stored[k]
        if set(a.get("held") or {}) != set(b["held"]):
            bad.append((k, "settings"))
            continue
        for nm in b["held"]:
            if a["held"][nm] != b["held"][nm] or a["render_sha256"][nm] != b["render_sha256"][nm]:
                bad.append((k, nm))
    return {"passed": not bad and set(new) == set(stored), "mismatches": bad}


def search_check_verdict(new, stored):
    """(Pure.) search-check: each part's evaluations equal the start of row (c)'s stored step-1 curve exactly, with the
    first render's sha256 the stored one's and no refusal. new, stored: {pkey: search record}. -> {passed, ...}."""
    bad = []
    for k in sorted(stored):
        a, b = new.get(k) or {}, stored[k]
        if "refused" in a or "step1" not in a:
            bad.append((k, "refused"))
            continue
        c = a["step1"]["curve"]
        if not c or c != b["step1"]["curve"][:len(c)]:
            bad.append((k, "curve"))
        if a["step1"]["start"]["render_sha256"] != b["step1"]["start"]["render_sha256"]:
            bad.append((k, "first render"))
    return {"passed": not bad and set(new) == set(stored), "mismatches": bad}


def dry_refusal(recs, build_parts, build_sha, dry_rec):
    """(Pure.) Why `answers` refuses, or None: the build file's sha256 must be main's phase_scratch_notes_dry and every
    answered search record's dry guitar sha256 that part's `tr-di` in the build (the true DI or avg+mild passed by
    mistake cannot repeat row (b) or (c) unseen)."""
    if not isinstance(dry_rec, dict) or dry_rec.get("sha256") != build_sha:
        return f"the build's sha256 is not main's {PHASE_DRY}"
    for k, r in sorted(recs.items()):
        if "refused" in r:
            continue
        want = ((build_parts.get(k) or {}).get("arms") or {}).get(DRY, {}).get("sha256")
        if not want or r.get("dry_sha256") != want:
            return f"{k}: the search record's dry guitar is not the hashed build's {DRY}"
    return None


def redo_hash_refusal(nr_main, build, transcribe_sha, pair):
    """(Pure.) Why the build may not drive the row, or None: main's phase_nr_1_redo_notes must hold the transcription
    record's sha256 and the build must come from it; main's phase_nr_1_redo_install must name the install's lock and
    model, and the build must come from that install."""
    rec = (nr_main or {}).get(NT.PHASE_NOTES)
    if not isinstance(rec, dict) or rec.get("sha256") != transcribe_sha:
        return f"the transcription record's sha256 is not main's {NT.PHASE_NOTES}"
    if build.get("transcribe_sha256") != transcribe_sha:
        return "the build was made from another transcription"
    if not isinstance((nr_main or {}).get(NT.PHASE_INSTALL), dict):
        return f"main's {NT.PHASE_INSTALL} names no install"
    why = NT.ledger_pair_refusal(nr_main, pair)
    if why:
        return why
    if tuple(build.get("pair") or ()) != tuple(pair):
        return "the build comes from another install"
    return None


def ear_refusal(nr_main, build_sha=None):
    """(Pure.) Why answers, score and read may not run on the ear check, or None: the ear verdict for `build_sha`
    must read ok (from the page's stored answers, `note_rebuild_ear.redo_verdict`). Each build is heard on its own
    page with its own verdict (`note_transcribe.ear_key`: the first build's `phase_nr_1_redo_ear`, a later one's
    `phase_nr_1_redo_ear_<sha12>`); no count of builds or fixes is kept (the user, 2026-11-24). Without `build_sha`,
    main's `phase_nr_1_redo_ear`."""
    nr = nr_main or {}
    if build_sha is None:
        rec = nr.get(NT.PHASE_EAR)
    else:
        heard = {k: v for k, v in nr.items() if (k == NT.PHASE_EAR or k.startswith(NT.PHASE_EAR + "_"))
                 and isinstance(v, dict) and "verdict" in v}
        found = [(k, v) for k, v in sorted(heard.items()) if v.get("dry_build_sha256") == build_sha]
        rec = found[0][1] if found else None
        if found and found[0][0] != NT.ear_key(build_sha):       # #581's nit: filed under its own key only
            return f"the verdict for {build_sha[:12]} is filed under {found[0][0]}, not {NT.ear_key(build_sha)}"
        if rec is None and heard:
            return f"main's ear verdicts were heard on clips from another build, not {build_sha[:12]}"
    if not isinstance(rec, dict) or "verdict" not in rec:
        return f"the redo's ear check is not recorded on main ({NT.ear_key(build_sha) if build_sha else NT.PHASE_EAR})"
    if rec["verdict"] != "ok":
        return f"the redo's ear check reads {rec['verdict']}: nothing is answered, scored or read"
    return None


def deciding_stop(refused, sets_of, deciding=DECIDING):
    """(Pure.) The row's refusals, the deciding parts' and the rest's apart. No row stops on a count of refusals (S1,
    phase_scratch_refusal_reports): "stopped" is always False; each refused part reads at Cen in the deciding read,
    the passing-only read beside. -> (deciding, panel, stopped)."""
    dec = sorted(k for k in refused if sets_of.get(k) in deciding)
    pan = sorted(k for k in refused if sets_of.get(k) not in deciding)
    return dec, pan, False


def paired_values(new, old, field):
    """(Pure.) Per part new[field] - old[field] where both exist. new, old: {pkey: part numbers or None}."""
    out = {}
    for k, a in new.items():
        b = old.get(k)
        if a is not None and b is not None and a.get(field) is not None and b.get(field) is not None:
            out[k] = a[field] - b[field]
    return out


def checks_passed(score_result, search_result):
    """(Pure.) Why `search` refuses on the checks, or None: both result files exist and passed."""
    for name, r in (("score-check", score_result), ("search-check", search_result)):
        if r is None:
            return f"{name} has not run"
        if not r.get("passed"):
            return f"{name} did not pass: {r.get('mismatches')}"
    return None


# --- paths --------------------------------------------------------------------------------------------------------------------

def notes_dir():
    return S.fs_dir() / ("notes" if not BUILD_NAME else f"notes-{BUILD_NAME}")


def dry_key(name=None):
    """(Pure.) A build's hash key in the ladder: the first build's `phase_scratch_notes_dry`, a later one's
    `phase_scratch_notes_dry_<name>` (#581's nit: fs-notes asks about a later build's own key)."""
    return PHASE_DRY if not name else f"{PHASE_DRY}_{name}"


def build1_read_refusal(ladder_main, name=None):
    """(Pure.) 12q R8's order guard: build 1's search (the ear-faulty build) is answered, scored and read only after a
    later build is hashed on main (`phase_scratch_notes_dry_<name>`), so its read cannot steer the later build's
    design. -> refusal or None (a later build: None)."""
    if name:
        return None
    if any(k.startswith(PHASE_DRY + "_") for k in (ladder_main or {})):
        return None
    return "build 1 is read only after a later build is hashed on main (12q R8: phase_scratch_notes_dry_<name>)"


def ear_label(nr_main, build_sha):
    """(Pure.) 12q R5: the ear verdict as a label beside a read, never a gate: "ear ok", "ear <verdict>" or "ear
    pending" (no verdict yet). The row's outcome code waits for a verdict."""
    why = ear_refusal(nr_main, build_sha)
    if why is None:
        return "ear ok"
    rec = next((v for k, v in (nr_main or {}).items() if isinstance(v, dict) and k.startswith(NT.PHASE_EAR)
                and v.get("dry_build_sha256") == build_sha), None)
    return f"ear {rec['verdict']}" if rec and "verdict" in rec else "ear pending"


def search_path(pk):
    return notes_dir() / "search" / f"{pk}.json"


def start_path(pk):
    return notes_dir() / "start-ref" / f"{pk}.json"


def answers_path():
    return notes_dir() / "answers.json"


def score_path(pk):
    return notes_dir() / "score" / f"{pk}.json"


def report_path():
    return notes_dir() / "report.json"


def rows_path():
    return notes_dir() / "rows.json"


def check_dir(kind):
    """`check-score` or `check-search`: never inside PF/fs/score/fs-both/."""
    if kind not in ("check-score", "check-search"):
        raise ValueError(kind)
    return notes_dir() / kind


# --- the guards ---------------------------------------------------------------------------------------------------------------

def notes_draw():
    """The from-scratch draw this row reads (`scratch_search.require_draw`), refused when it holds a DI the user
    ruled out (12p, `note_transcribe.ruled_out_refusal`)."""
    draw = S.require_draw()
    why = NT.ruled_out_refusal([p["unit"] for p in draw["parts"]], "fs-notes's draw")
    if why:
        raise SystemExit(why)
    return draw


def require_row(*nr_phases, ladder=()):
    """Refuse unless this checkout runs main's redo and main holds this row's declaration, row (c)'s audited outcome,
    the redo's declaration and `nr_phases` / `ladder`. -> {ledger id: main's entry}."""
    fn_table_guard()
    m = NT.require_redo(ladder=(GATE, PHASE))
    for lid, keys in ((NT.LEDGER_ID, nr_phases), (LEDGER_ID, ladder)):
        for k in keys:
            if k not in (m.get(lid) or {}):
                raise SystemExit(f"main's {lid} entry has no {k}: merge it before running")
    return m


def check_result(kind):
    p = check_dir(kind) / "result.json"
    return json.loads(p.read_text()) if p.exists() else None


def build_refusal(build):
    """(Pure.) The build's stop rule, or None. Nothing stops it now: a failing ear item is a report (12q, R1) and a
    count of content-check failures stops nothing (S1): a content check is a label on its part."""
    return None


def require_build(m):
    """The redo build, refused unless its sha256 is main's phase_scratch_notes_dry, it comes from main's hashed
    notes and install, and the stop rule holds (`build_refusal`)."""
    b = NT.require_file_hash(m.get(LEDGER_ID), dry_key(BUILD_NAME), NT.build_path(BUILD_NAME))
    why = redo_hash_refusal(m.get(NT.LEDGER_ID), b, NT.NR.file_sha(NT.transcribe_path()),
                            NT.install_pair(NT.load_manifest())) or build_refusal(b)
    if why:
        raise SystemExit(why)
    return b


def require_install_record(m):
    """Refuse unless main's phase_nr_1_redo_install holds this install's lock and model and the sha256 of the install
    gate and calibration records the build read."""
    why = NT.install_record_refusal((m.get(NT.LEDGER_ID) or {}).get(NT.PHASE_INSTALL),
                                    NT.NR.file_sha(NT.gate_path()), NT.NR.file_sha(NT.calibration_path()),
                                    NT.install_pair(NT.load_manifest()))
    if why:
        raise SystemExit(why)


def comparator_answers():
    """Row (c)'s answers, refused unless their sha256 is main's phase_fs_answers_both."""
    return S.require_hash(S.phase_answers(COMPARATOR), S.answers_path(COMPARATOR))


# --- the checks (renders, once, after the merge) --------------------------------------------------------------------------

def cmd_score_check(_args):
    """Step 4 (about 40 renders), once: the first BKS and the first GOAT part of row (c)'s hashed answers re-scored
    through `scratch_search.score_row_part`, the path this row's score takes; every render's sha256 and held value must
    equal row (c)'s stored score file. -> check-score/<part>.json and result.json (never into score/fs-both/)."""
    require_row()
    d = check_dir("check-score")
    NT.never_overwrite(d / "result.json")
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import pipeline_fix as P

    R.no_separation_beside()
    draw = notes_draw()
    ans = comparator_answers()
    sd = R.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    by = {p["pkey"]: p for p in draw["parts"]}
    LO._wait_cap()
    new, stored, total = {}, {}, 0
    for k in check_parts(draw["parts"]):
        out = d / f"{k}.json"
        NT.never_overwrite(out)
        rec, used = S.score_row_part(by[k], ans["parts"][k], ans["parts"], COMPARATOR, S.file_sha(
            S.answers_path(COMPARATOR)), sd, CB.new_renderer)
        total += used
        P.save(out, rec)
        new[k], stored[k] = rec, json.loads(S.score_path(COMPARATOR, k).read_text())
    res = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "renders": total, **score_check_verdict(new, stored),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(d / "result.json", res)
    print(f"SCORE-CHECK {'PASS' if res['passed'] else 'FAIL'}: {total} renders; mismatches {res['mismatches']}")


def cmd_search_check(_args):
    """Step 4 (about 12 renders a part), once: on the same two parts, `scratch_search.run_part` with avg+mild as the
    dry guitar (passed as this row passes `tr-di`, with its sha256), row (c)'s start reference passed explicitly and a
    step-1 budget of CHECK_BUDGET, stopped after step 1; its evaluations must equal the start of row (c)'s stored
    step-1 curve exactly. -> check-search/<part>.json and result.json."""
    require_row()
    d = check_dir("check-search")
    NT.never_overwrite(d / "result.json")
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import pipeline_fix as P

    R.no_separation_beside()
    draw = notes_draw()
    sd = R.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    blur = json.loads((R.replay_dir() / "blur.json").read_text())
    if blur["draw_sha256"] != draw["replay_draw_sha256"]:
        raise SystemExit("blur.json was made from another replay draw")
    by, rby = {p["pkey"]: p for p in draw["parts"]}, {p["pkey"]: p for p in R.require_draw()["parts"]}
    lists = C.mic_lists()
    LO._wait_cap()
    new, stored, total = {}, {}, 0
    for k in check_parts(draw["parts"]):
        out = d / f"{k}.json"
        NT.never_overwrite(out)
        p = by[k]
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        x32 = R.load_dry("avg+mild", rby[k], R.di_section(prt), blur)
        rec = S.run_part(p, "avg+mild", REF, x32, S.load_ref_blank(sd, p, REF), CB.new_renderer, lists,
                         budget=CHECK_BUDGET, start_ref=p["start_ref"]["avg+mild"][REF],
                         dry_sha256=blur["parts"][k]["sha256"]["avg+mild"], step1_only=True)
        total += rec.get("renders", 0)
        P.save(out, rec)
        new[k], stored[k] = rec, json.loads(S.search_path(COMPARATOR, k).read_text())
    res = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "renders": total, "budget": CHECK_BUDGET,
           **search_check_verdict(new, stored), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(d / "result.json", res)
    print(f"SEARCH-CHECK {'PASS' if res['passed'] else 'FAIL'}: {total} renders; mismatches {res['mismatches']}")


# --- the row ------------------------------------------------------------------------------------------------------------------

def first_evaluation(p):
    """(Pure.) The settings `run_part`'s step 1 renders first for a part, in the renderer's form: `coord_search`
    evaluates its start through the canon it is given (C1a's), then `sx1`."""
    from learn import full_controls as F
    from learn import local_objective as LO

    start = F.c1a_start(p["cen"]["settings"], p["amp"])
    return LO.tdict(LO.sdict(F.make_canon(p["amp"])(start)))


def start_reference(p, x32, ref_blank, new_renderer, path, dry_sha):
    """The row's start reference for a part: the exact first evaluation step 1 asks for (`sx1` of Cen in C1a's start
    form as `coord_search` evaluates it, through C1a's canon; `first_evaluation`) through `tr-di` in its own fresh
    primed process (2 renders), judged on the search half as `run_part` judges, written once just before the part's
    search (an existing file for the same dry guitar is the reference). It refuses a part whose first evaluation is
    not `sx1(start)`, `run_part`'s priming (equal on all 47 parts at declaration). -> (the value, renders used)."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import full_controls as F
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    if path.exists():
        rec = json.loads(path.read_text())
        if rec["dry_sha256"] != dry_sha:
            raise SystemExit(f"{path.name}: a start reference for another dry guitar")
        return rec["value"], 0
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    dj = np.asarray(x32, np.float64)[trim[0]:trim[1]]
    xs = first_evaluation(p)
    if xs != LO.tdict(LO.sdict(F.c1a_start(p["cen"]["settings"], p["amp"]))):
        raise SystemExit(f"{p['pkey']}: the first evaluation is not run_part's priming sx1(start): an amendment first")
    y = np.asarray(AM.fresh_render(new_renderer, x32, p["cen"]["select"], xs, xs), np.float64)[trim[0]:trim[1]]
    v = R.half_distance(ref_blank, y, dj, p["lag"], p["search"]) if np.isfinite(y).all() else math.inf
    P.save(path, {"plan": PLAN, "part": p["pkey"], "dry": DRY, "dry_sha256": dry_sha, "value": v,
                  "render_sha256": AM.audio_sha(np.nan_to_num(y)), "renders": 2,
                  "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    return v, 2


def cmd_search(args):
    """One shard of the row's searches (renders), after both checks passed and the build is hashed: per part (sorted
    by key, every n-th), a content-refused part's record written as refused (no render); else the start reference,
    then `scratch_search.search_row_part` with `tr-di` as the dry guitar (its sha256 in the record) against `xlnoG@-3`
    zeroed outside the search half. The disk guard before every part; at most 3 shards."""
    m = require_row(NT.PHASE_INSTALL, NT.PHASE_NOTES, ladder=(PHASE_DRY,))
    why = checks_passed(check_result("check-score"), check_result("check-search"))
    if why:
        raise SystemExit(why)
    build = require_build(m)
    require_install_record(m)
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    R.no_separation_beside()
    draw = notes_draw()
    sd = R.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    k_, n_ = args.shard
    mine = [p for j, p in enumerate(sorted(draw["parts"], key=lambda p: p["pkey"])) if j % n_ == k_]
    if args.first:
        mine = mine[:args.first]
    lists = C.mic_lists()
    LO._wait_cap()
    total, t0 = 0, time.time()
    for p in mine:
        out = search_path(p["pkey"])
        if getattr(args, "rerun", False):                # S1: a technical refusal, once more in this fresh process
            if not out.exists() or not S.refused_record(json.loads(out.read_text())):
                continue
            out = S.rerun_path(out)
        if out.exists():
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        row = build["parts"][p["pkey"]]
        if row["failed"]:                              # S1: a content check is a label, never a refusal
            print(f"{p['pkey'][-60:]}: content checks {row['failed']} (a label; searched as built)", flush=True)
        x32 = NT.load_dry(DRY, p["pkey"], build)
        sha = row["arms"][DRY]["sha256"]               # the hashed build's (phase_scratch_notes_dry)
        if S.npy_sha(x32) != sha:                      # the audio itself, before any render
            raise SystemExit(f"{p['pkey']}: the loaded dry guitar is not the hashed build's {DRY}")
        ref_blank = S.load_ref_blank(sd, p, REF)
        sref, used = start_reference(p, x32, ref_blank, CB.new_renderer, start_path(p["pkey"]), sha)
        rec = S.search_row_part(p, DRY, REF, x32, ref_blank, CB.new_renderer, lists, out, f"{LEDGER_ID} {PHASE}",
                                start_ref=sref, dry_sha256=sha)
        if row["failed"]:
            rec["content_label"] = row["failed"]
            P.save(out, rec)
        total += rec.get("renders", 0) + used
        if "refused" in rec:
            print(f"{p['pkey'][-60:]}: REFUSED {rec['refused']}", flush=True)
        print(f"shard {k_}/{n_}: {total} renders in {time.time() - t0:.0f} s "
              f"({total / max(1, time.time() - t0) * 3600:.0f} an hour)", flush=True)
    print(f"FS-NOTES SEARCH DONE {k_}/{n_}: {total} renders in {time.time() - t0:.0f} s")


def cmd_answers(_args):
    """The row's answers (zero renders): every search record's dry guitar checked against the hashed build
    (`dry_refusal`); a technical refusal's rerun used when it passed (`scratch_search.with_reruns`; one not yet rerun
    waits); `scratch_search.answer_parts`; the refusals reported (`deciding_stop`, `refusal_report`), never a stop.
    -> answers.json; its sha256 into the ledger as phase_scratch_notes_answers before `score`."""
    m = require_row(NT.PHASE_INSTALL, NT.PHASE_NOTES, ladder=(dry_key(BUILD_NAME),))
    why = build1_read_refusal(m.get(LEDGER_ID), BUILD_NAME)
    if why:
        raise SystemExit(why)
    ear = ear_label(m.get(NT.LEDGER_ID), ((m.get(LEDGER_ID) or {}).get(dry_key(BUILD_NAME)) or {}).get("sha256"))
    build = require_build(m)
    NT.never_overwrite(answers_path())
    from learn import pipeline_fix as P

    draw = notes_draw()
    for p in draw["parts"]:
        if not search_path(p["pkey"]).exists():
            raise SystemExit(f"{p['pkey']}: not searched")
    recs, used, reruns = S.with_reruns([p["pkey"] for p in draw["parts"]], search_path)
    why = S.rerun_refusal(reruns)
    if why:
        raise SystemExit(why)
    why = dry_refusal(recs, build["parts"], NT.NR.file_sha(NT.build_path(BUILD_NAME)),
                      (m.get(LEDGER_ID) or {}).get(dry_key(BUILD_NAME)))
    if why:
        raise SystemExit(why)
    parts, refused = S.answer_parts(draw, recs, lambda k: S.file_sha(used[k]))
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    dec, pan, stop = deciding_stop(refused, sets_of)
    out = {"plan": PLAN, "row": ROW, "dry": DRY, "ref": S.REF_NAME[REF], "draw_sha256": S.file_sha(S.draw_path()),
           "build_sha256": NT.NR.file_sha(NT.build_path()), "time": time.strftime("%Y-%m-%d %H:%M:%S"),
           "renders": sum(r.get("renders", 0) for r in recs.values()), "refused": refused,
           "refused_deciding": dec, "refused_panel": pan, "stopped": stop, "reruns": reruns,
           "refusal_report": S.refusal_report(refused, sets_of, DECIDING), "parts": parts}
    P.save(answers_path(), out)
    print(f"FS-NOTES ANSWERS: {len(parts)} parts, {len(refused)} refused ({len(dec)} of the 40 deciding, each read "
          f"at Cen; panel {pan}); reruns {reruns}; sha256 {S.file_sha(answers_path())} (into the ledger as "
          f"{PHASE_ANSWERS} before `score`)")


def cmd_score(args):
    """One shard of the row's score (renders): `scratch_search.score_row_part` on the hashed answers, exactly as rows
    (b) and (c) were scored. -> score/<part>.json."""
    m = require_row(NT.PHASE_INSTALL, NT.PHASE_NOTES, ladder=(dry_key(BUILD_NAME), PHASE_ANSWERS))
    why = build1_read_refusal(m.get(LEDGER_ID), BUILD_NAME)
    if why:
        raise SystemExit(why)
    ear = ear_label(m.get(NT.LEDGER_ID), ((m.get(LEDGER_ID) or {}).get(dry_key(BUILD_NAME)) or {}).get("sha256"))
    print(f"{ROW}: {ear} (12q R5: a label beside the read; the outcome code waits for the ear verdict)")
    ans = NT.require_file_hash(m.get(LEDGER_ID), PHASE_ANSWERS, answers_path())
    if ans.get("stopped"):                               # no answers file is written stopped since S1
        raise SystemExit(f"{ROW}'s answers were written stopped: nothing is scored")
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    R.no_separation_beside()
    draw = notes_draw()
    sd = R.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    k_, n_ = args.shard
    mine = [p for j, p in enumerate(sorted(draw["parts"], key=lambda p: p["pkey"])) if j % n_ == k_]
    LO._wait_cap()
    total, t0 = 0, time.time()
    for p in mine:
        out = score_path(p["pkey"])
        a = ans["parts"].get(p["pkey"])
        if getattr(args, "rerun", False):                # S1: a scoring-control miss, once more in this fresh process
            if a is None or not out.exists() or json.loads(out.read_text())["scoring_control_ok"]:
                continue
            out = S.rerun_path(out)
        if a is None or out.exists():
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        rec, used = S.score_row_part(p, a, ans["parts"], ROW, S.file_sha(answers_path()), sd, CB.new_renderer)
        total += used
        P.save(out, rec)
        print(f"{p['pkey'][-60:]}: scored {rec['distinct_renders']} settings; scoring control "
              f"{'ok' if rec['scoring_control_ok'] else 'MISS'}; {total} renders, {time.time() - t0:.0f} s", flush=True)
    print(f"FS-NOTES SCORE DONE {k_}/{n_}: {total} renders in {time.time() - t0:.0f} s")


def bks_goat(row, sub="all"):
    """(Pure.) A `note_replay.summary` row pooled on BKS+GOAT (`full_controls_c3r.pooled`), on all parts or one class."""
    from learn import full_controls_c3r as R

    rows = {s: (row.get(s) or {}) if sub == "all" else ((row.get(s) or {}).get(sub) or {}) for s in DECIDING}
    return R.pooled(rows) if all(v.get("mean") is not None for v in rows.values()) else None


def set_rows(sd, draw, values, keys=None):
    """`note_replay.summary` of per-part values on the parts given (all by default), with BKS+GOAT pooled on all, clean
    and crunch. values: {pkey: value}."""
    from learn import note_replay as R

    parts = [dict(p, cluster=p["cluster"].split("|", 1)[1]) for p in draw["parts"]
             if values.get(p["pkey"]) is not None and (keys is None or p["pkey"] in keys)]
    if not parts:
        return None
    row = R.summary(sd.units, parts, values, R.lender_band())
    row["bks_goat"] = {s: bks_goat(row, s) for s in SUBSETS}
    return row


def cmd_read(_args):
    """The row's reading (zero renders), once: the per-part numbers (`scratch_search.read_row_parts`) of this row and of
    row (c) (its hashed answers and score files), the refusal stop on the 40, then per arm D_notes and the arm's own G
    on BKS+GOAT (the 40, clean, crunch; row (c)'s bar on exactly the parts this row scores), saved before FN_TABLE's
    code; beside: G and I on the pool, D_notes on the pool and on the panel by its MedleyDB and Laminar Flow files, each
    set's leave-one-cluster-out range, D with refused parts as Cen, the shrunk answer against row (c)'s full answer,
    the answer less the shrunk answer, the parts at +0.10 or worse, the share of row (b)'s gain kept, the
    checkpoints, the search-half gain against held G, tr-plain's checks, and the bottleneck with D_notes by `ring-kept`'s
    figure, the share of bent notes and the share of chords (`part_figures`, `by_figure`). -> rows.json, report.json."""
    m = require_row(NT.PHASE_INSTALL, NT.PHASE_NOTES, ladder=(dry_key(BUILD_NAME), PHASE_ANSWERS))
    why = build1_read_refusal(m.get(LEDGER_ID), BUILD_NAME)
    if why:
        raise SystemExit(why)
    ear = ear_label(m.get(NT.LEDGER_ID), ((m.get(LEDGER_ID) or {}).get(dry_key(BUILD_NAME)) or {}).get("sha256"))
    print(f"{ROW}: {ear} (12q R5: a label beside the read; the outcome code waits for the ear verdict)")
    ans = NT.require_file_hash(m.get(LEDGER_ID), PHASE_ANSWERS, answers_path())
    NT.never_overwrite(report_path())
    NT.never_overwrite(rows_path())
    build = require_build(m)
    from learn import note_replay as R
    from learn import pipeline_fix as P

    draw = notes_draw()
    sd = R.Stored()
    rby = {p["pkey"]: p for p in R.require_draw()["parts"]}
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    per, refused, replaced, ctl = S.read_row_parts(draw, ans, S.file_sha(answers_path()), score_path, sd, rby)
    dec, pan, stop = deciding_stop(refused, sets_of)
    out = {**S.report_body(ROW, "notes", S.file_sha(answers_path()), per, refused, replaced, ctl), "ear": ear,
           "code_provisional": ear != "ear ok",            # 12q R5: the FN code is provisional while the ear is pending
           "refused_deciding": dec, "refused_panel": pan, "stopped": stop,
           "refusal_report": S.refusal_report(refused, sets_of, DECIDING)}
    passing = per
    per = S.itt_per(per, refused)                        # S1: the deciding read on every part, a refused one at Cen
    c_ans = comparator_answers()
    per_c = S.read_row_parts(draw, c_ans, S.file_sha(S.answers_path(COMPARATOR)),
                             lambda k: S.score_path(COMPARATOR, k), sd, rby)[0]
    b_ans = S.require_hash(S.phase_answers(STEM_ROW), S.answers_path(STEM_ROW))
    per_b = S.read_row_parts(draw, b_ans, S.file_sha(S.answers_path(STEM_ROW)),
                             lambda k: S.score_path(STEM_ROW, k), sd, rby)[0]
    scored = {k for k, v in per.items() if v is not None}
    arms, beside = {}, {}
    for arm, f in ARMS.items():
        d = paired_values(per, per_c, f)
        g = {k: per[k][f] for k in scored}
        gc = {k: per_c[k][f] for k in scored if per_c.get(k)}
        rd, rg, rc = set_rows(sd, draw, d), set_rows(sd, draw, g), set_rows(sd, draw, gc)
        if rd is None or rg is None or rc is None:
            raise SystemExit(f"{arm}: no part carries both rows' numbers")
        arms[arm] = {"D": rd["bks_goat"], "G": rg["bks_goat"], "bar_fs_both": rc["bks_goat"]}
        as_cen = dict(d, **{k: -per_c[k][f] for k in per_c if per_c.get(k) and per.get(k) is None})
        onsets = {k: (build["parts"][k]["arms"][DRY]["figures"].get("onsets-found") or {}).get("share")
                  for k in d if sets_of[k] in DECIDING}
        lower, upper = median_split(onsets)
        low, up = set_rows(sd, draw, d, set(lower)), set_rows(sd, draw, d, set(upper))
        names, diff = bottleneck((up or {}).get("bks_goat", {}).get("all"), (low or {}).get("bks_goat", {}).get("all"))
        beside[arm] = {"D_rows": rd, "G_rows": rg, "D_refused_as_cen": (set_rows(sd, draw, as_cen) or {}).get(
                           "bks_goat"),
                       "parts_at_or_over_0.10": sorted(k for k, v in g.items() if v >= BIG),
                       "bottleneck": {"names": names, "difference": diff, "lower": lower, "upper": upper,
                                      "by_figure": {}}}
        dec = {k: v for k, v in d.items() if sets_of[k] in DECIDING}
        for name, vals in part_figures(build["parts"], dec).items():     # beside the bottleneck, inside this read
            fig = by_figure(dec, vals)
            fig["rows"] = {h: ((set_rows(sd, draw, d, set(fig[h])) or {}).get("bks_goat") or {}).get("all")
                           for h in ("lower", "upper")}
            beside[arm]["bottleneck"]["by_figure"][name] = fig
    man = NT.load_manifest()
    idx_ok = NT.MEDLEYDB_INDEX.exists() and man.get("medleydb_index_sha256") == NT.NR.file_sha(NT.MEDLEYDB_INDEX)
    beside["transcriber_overlap"] = (NT.transcriber_overlap_songs(draw["parts"], NT.medleydb_index_ids(
        json.loads(NT.MEDLEYDB_INDEX.read_text()))) if idx_ok else "the index is not the manifest's: not read")
    dA = paired_values(per, per_c, "G")
    beside["panel_split"] = {}
    for grp in ("medleydb", "laminar_flow"):
        ks = sorted(p["pkey"] for p in draw["parts"] if NT.panel_group(p) == grp and p["pkey"] in dA)
        beside["panel_split"][grp] = {"parts": ks, "mean": sum(dA[k] for k in ks) / len(ks) if ks else None}
    beside["shrunk_less_fs_both_answer"] = (set_rows(sd, draw, {k: per[k]["G_shrunk"] - per_c[k]["G"] for k in dA
                                                                if per[k].get("G_shrunk") is not None})
                                            or {}).get("bks_goat")
    beside["answer_less_shrunk"] = (set_rows(sd, draw, {k: per[k]["G"] - per[k]["G_shrunk"] for k in scored
                                                        if per[k].get("G_shrunk") is not None}) or {}).get("bks_goat")
    gb = set_rows(sd, draw, {k: per_b[k]["G"] for k in scored if per_b.get(k)})
    gn = beside["answer"]["G_rows"]
    beside["share_of_row_b_gain"] = share_of(((gn or {}).get("bks_goat") or {}).get("all"),
                                            ((gb or {}).get("bks_goat") or {}).get("all"))
    rows_full = S.summarise_row(sd, draw, per)
    gain = {}
    for k in scored:
        sr = json.loads(search_path(k).read_text())
        if "step1" in sr and sr["step1"]["curve"]:
            gain[k] = math.log(sr["final_fresh"]["value"] / sr["step1"]["curve"][0]) \
                if S.finite_pos(sr.get("final_fresh", {}).get("value")) else None
    pairs = [(gain[k], per[k]["G"]) for k in gain if gain[k] is not None]
    beside["search_gain_vs_held_G"] = _pearson(pairs)
    beside["tr_plain"] = {k: {"failed": r["arms"]["tr-plain"]["failed"], "passes": r["arms"]["tr-plain"]["passes"]}
                          for k, r in build["parts"].items()}
    rows = {"arms": arms, "beside": beside, "rows": rows_full,
            "reading_pool": S.row_reading(rows_full["G"]["deciding_pool"], rows_full["I"]["deciding_pool"])}
    arms_pass = None
    if refused:                                          # beside: the passing-only read
        arms_pass = {}
        for arm, f in ARMS.items():
            dp = paired_values(passing, per_c, f)
            gp = {k: passing[k][f] for k in dp}
            gcp = {k: per_c[k][f] for k in dp}
            rdp, rgp, rcp = set_rows(sd, draw, dp), set_rows(sd, draw, gp), set_rows(sd, draw, gcp)
            arms_pass[arm] = {"D": (rdp or {}).get("bks_goat"), "G": (rgp or {}).get("bks_goat"),
                              "bar_fs_both": (rcp or {}).get("bks_goat")}
        rows["arms_passing_only"] = arms_pass
        rows["refused_audit"] = S.refused_audit(draw["parts"], refused, R.lender_band(),
                                                values=paired_values(per, per_c, "G"))
    P.save(rows_path(), dict(out, rows=rows))           # the rows are saved before the code is read
    fn = fn_code(arms)
    fn_pass = fn_code(arms_pass) if arms_pass and all((a["D"] or {}).get("all") for a in arms_pass.values()) else fn
    label = S.refusal_label(fn["code"], fn_pass["code"])
    P.save(report_path(), dict(out, rows=rows, fn=fn, code=fn["code"], fn_passing_only=fn_pass, label=label,
                               next="to the user with both reads" if label else None))
    for arm in ARMS:
        a = arms[arm]["D"]["all"] or {}
        print(f"{ROW} {arm}: D_notes on the 40 {a.get('mean')} [{a.get('lo90')}, {a.get('hi90')}] -> "
              f"{(fn['readings'][arm]['all'] or {}).get('reading')}")
    print(f"FN {fn['code']}{' (' + fn['arm'] + ')' if fn.get('arm') else ''}: {fn['reading']}. Recommendation: "
          f"{fn['licence']}{'; ' + str(fn['lean']) if fn.get('lean') else ''}")


def _pearson(pairs):
    """(Pure.) Pearson's r of [(x, y)], or None under 3 pairs."""
    if len(pairs) < 3:
        return None
    mx = sum(x for x, _ in pairs) / len(pairs)
    my = sum(y for _, y in pairs) / len(pairs)
    sxy = sum((x - mx) * (y - my) for x, y in pairs)
    sx = math.sqrt(sum((x - mx) ** 2 for x, _ in pairs))
    sy = math.sqrt(sum((y - my) ** 2 for _, y in pairs))
    return sxy / (sx * sy) if sx and sy else None


COMMANDS = {"score-check": cmd_score_check, "search-check": cmd_search_check, "search": cmd_search,
            "answers": cmd_answers, "score": cmd_score, "read": cmd_read}


def main(argv=None):
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    for p_ in (str(root), str(root / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--shard", type=S._shard, default=(0, 1))
    ap.add_argument("--first", type=int, default=0, help="search only this shard's first n parts (the re-timing)")
    ap.add_argument("--build-name", dest="build_name", default=None, help="a later build (12q): its own dry key and "
                    "folders")
    ap.add_argument("--rerun", action="store_true",
                    help="search or score again, once, only the parts whose record refused (S1: then Cen)")
    args = ap.parse_args(argv)
    global BUILD_NAME
    BUILD_NAME = args.build_name
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
