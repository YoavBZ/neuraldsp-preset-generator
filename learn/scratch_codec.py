"""The from-scratch search's `fs-codec` row, the codec ceiling: can a dry guitar that passed through a latent codec
still drive the search? (`docs/scratch-search-plan.md` section 12, "The `fs-codec` row"; ledger `preset-ladder`
`phase_scratch_codec`, then `phase_scratch_codec_dry`, `phase_scratch_codec_answers_m2l`, `..._dac`, and only after an
`FK-shut` `..._m2l_full` or `..._dac_full`; `phase_scratch_codec_outcome`.)

`fs-codec` = (the codec's dry guitar, `xlnoG`): the **true DI after a codec round trip** (`learn/codec_roundtrip.py`,
then the measure step) is the dry guitar of every search render and the judge's DI; the search-half reference is
`xlnoG@-3` with everything outside the search half zeros. Same draw (`phase_fs_draw`), Cen, halves and lag as rows (b)
and (c). The search stops at 50 evaluations (`run_part(budget=50, step1_only=True)`: 1 priming render and exactly the
first 50 evaluations of a 200-evaluation search); its answer is the 50-evaluation incumbent `cp50`, scored through the
true DI on the held half against the clean record by `scratch_search.score_row_part`. One number a part, `G50` =
ln(cp50 / Cen); read paired against rows (b) and (c): `D_true` = G50(fs-codec) - G50(fs-stem), `D_blur` = G50(fs-codec)
- G50(fs-both); `FK_TABLE`'s code from both on the full pool. Only after an `FK-shut`, the codec's full row runs through
`search_row_part`, `answer_parts`, `score_row_part` and `read_row_parts` unchanged, and the park stands only if both
arms read `FK-shut`.

    $MAIN -m learn.scratch_codec prep                         # zero renders: the raw sections and the next second
    # the round trips, each in its own venv (learn/codec_roundtrip.py's docstring)
    $MAIN -m learn.scratch_codec build                        # zero renders: measure, checks, figures; -> phase_scratch_codec_dry
    $MAIN -m learn.scratch_codec start --name rt-m2l --shard 0/3   # 2 renders a part (rt-id: the 2 check parts)
    $MAIN -m learn.scratch_codec control                      # 22 renders, once
    $MAIN -m learn.scratch_codec search --name rt-m2l --shard 0/3 [--first 2]   # 51 renders a part
    $MAIN -m learn.scratch_codec answers --name rt-m2l        # zero renders; its sha256 -> phase_scratch_codec_answers_m2l
    $MAIN -m learn.scratch_codec score --name rt-m2l --shard 0/3   # 4 renders a part; the only step that reads a held half
    $MAIN -m learn.scratch_codec read --name rt-m2l           # zero renders, once: D_true, D_blur, FK_TABLE's code
    # only after that codec's report reads FK-shut: search-full, answers-full, score-full, read-full --name <codec>

Every command refuses unless this checkout runs main's code (`scratch_search.on_main`, this module and
`learn/codec_roundtrip.py` equal main's, the `phase_scratch_codec*` keys equal main's), main's blob of
`learn/scratch_search.py` is the one `fs-notes`' two checks passed on, main holds `phase_fs`, `phase_fs_draw`,
`phase_scratch_both_outcome` and `phase_scratch_codec`, and `fs-notes`' two checks have passed. It edits neither
`learn/scratch_search.py` nor `learn/scratch_notes.py`.

The pure parts (`fk_code`, `FK_TABLE` and its guard, `park_code`, `park_lifts`, `covers`, the answers' refusals, the
refusal stop) are tested in tests/test_scratch_codec.py on the light CI runner (no numpy).
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import subprocess
import time

from learn import scratch_notes as SN
from learn import scratch_search as S

LEDGER_ID = S.LEDGER_ID                  # preset-ladder
PLAN = "docs/scratch-search-plan.md section 12"
PHASE = "phase_scratch_codec"            # this declaration
PHASE_DRY = "phase_scratch_codec_dry"    # build.json's sha256: before any render
PHASE_OUTCOME = "phase_scratch_codec_outcome"
KEY_PREFIX = "phase_scratch_codec"
GATE = "phase_scratch_both_outcome"      # row (c)'s audited F-both on main
ROW = "fs-codec"
REF = "xlnoG"
STEM_ROW, BOTH_ROW = "fs-stem", "fs-both"     # rows (b) and (c): D_true and D_blur's comparators
NAMES = ("rt-m2l", "rt-m2l-b", "rt-dac", "rt-id", "rt-rs")
SEARCHED = ("rt-m2l", "rt-dac")          # a short row each
START_NAMES = ("rt-m2l", "rt-m2l-b", "rt-dac", "rt-id")
SHORT = {"rt-m2l": "m2l", "rt-dac": "dac"}
VENV_OF = {"rt-m2l": "codec", "rt-m2l-b": "codec", "rt-id": "codec", "rt-dac": "dac", "rt-rs": "dac"}
CODE_FILES = ("learn/scratch_codec.py", "learn/codec_roundtrip.py")
SCRATCH_SEARCH_BLOB = "b66af002f56242a6128a4719479c90f4d5abd319"   # S1's re-pin (fs-notes' checks ran on 2420043a;
#   the search and score path they ran through is unchanged: tests/test_refusal_reports.py)
CHECK_SHA256 = {"check-score": "727fda89a58afb45d6bf1ee923f7daaedcae70077a3556a3b3c714bb9d765b73",
                "check-search": "172e1c9ff509cf05db4a1d4c343f6131bc01876a6e1b8deb807fd6725aa1c545"}
BUDGET = 50                              # the short row: step 1 to 50 evaluations
CHECKPOINT = "50"                        # the answer: step 1's incumbent at 50 evaluations
CONTROL_BUDGET = 10                      # `rt-id` through this module's search path, against row (b)'s records
SMALL, BIG = S.SMALL, S.BIG              # 0.05, 0.10 (the user's rule)
SECTION, IN_LEN, NEXT = 492000, 540000, 48000
TIMING_MS = 1.0                          # the timing check: the 1-ms envelope's lag within this
TIMING_STOP = 3                          # this many parts beyond it stop the build
LUFS, LUFS_TOL = -22.9, 0.25            # the measure step's level on every measured DI (lufs_beyond)
MUSDB_TRAIN_PANEL = ("Big Troubles",)    # "BigTroubles - Phantom": MUSDB18 train (DAC trained on it, as a mix)
COMPRESSION = {"d_50": 0.141, "d_answer": 0.167, "compression": 0.026, "b_after_50": -0.044, "c_after_50": -0.018}
COMPRESSION_NOTE = ("the checkpoint compresses differences: (c) less (b) is +0.141 at 50 evaluations and +0.167 at the "
                    "final answer (+0.026); row (b) gains -0.044 after the checkpoint, row (c) -0.018, so a weaker dry "
                    "guitar falls further behind later. It leans D_true toward FK-clear and D_blur toward FK-shut or "
                    "undecided; the calibration rests on one pair of rows (b) and (c)")
MEASURE_CAVEAT = ("D_blur favours the codec: the measure step equalises the codec's output to the average balance "
                  "(removing its long-term spectral error) and keeps the true DI's +-15 dB clip offset, while avg+mild "
                  "was never re-measured and pays for both; D_true is clean (both sides measured alike)")


def phase_answers(name, full=False):
    """The ledger key of a codec row's answers' sha256 (`phase_scratch_codec_answers_m2l`, ..._dac, ..._m2l_full,
    ..._dac_full)."""
    if name not in SHORT:
        raise SystemExit(f"{name!r} has no row (only {list(SHORT)})")
    return f"{KEY_PREFIX}_answers_{SHORT[name]}" + ("_full" if full else "")


# --- the table (pure) --------------------------------------------------------------------------------------------------------

FK_TABLE = (    # (code, when, reading, what follows, the number it rests on); the first that holds
    ("FK-clear", "D_true's upper end under +0.10 and its mean under +0.05",
     "at the checkpoint, a cost of 0.10 or more against the true DI is ruled out; a cost of 0.05 to 0.10 is not",
     "the route is not ruled out by its codec. A weak go: LOUDAR's second test may be proposed, under its own "
     "declaration, timed on one clip first", "D_true"),
    ("FK-above", "D_blur's whole interval below zero and its mean at -0.05 or beyond",
     "the ceiling is above the blur as measured, at the cost D_true shows; by a heard size only at -0.10 or beyond",
     "not ruled out, with little room. A weak go, weaker than FK-clear: a rebuild that loses more than the room left "
     "lands at the blur", "D_blur"),
    ("FK-shut", "D_blur's lower end at -0.05 or above",
     "even a perfect input leaves no readable gain over the blur, although D_blur favours the codec",
     "the full row runs first; if it confirms (both arms FK-shut), the route is parked, not closed. Audited "
     "adversarially before any park is written", "D_blur"),
    ("FK-undecided", "anything else", "not decided; undecided is not failed",
     "to the user with the interval and what it rules out", "D_true and D_blur"),
)
FK_CODES = tuple(c for c, *_ in FK_TABLE)
FAVOUR = ("FK-clear", "FK-above", "FK-undecided", "FK-shut")     # park_code: the more favourable first
CAVEAT_CODES = ("FK-above", "FK-shut")


def _iv_ok(iv):
    return isinstance(iv, dict) and all(isinstance(iv.get(k), (int, float)) and math.isfinite(iv[k])
                                        for k in ("mean", "lo90", "hi90"))


def fk_holds(d_true, d_blur, small=SMALL, big=BIG):
    """(Pure.) Which of the table's conditions hold (before "first that holds"). -> {code: bool}."""
    return {"FK-clear": d_true["hi90"] < big and d_true["mean"] < small,
            "FK-above": d_blur["hi90"] < 0 and d_blur["mean"] <= -small,
            "FK-shut": d_blur["lo90"] >= -small,
            "FK-undecided": True}


def fk_code(d_true, d_blur, small=SMALL, big=BIG):
    """(Pure.) FK_TABLE's code: the first that holds. d_true, d_blur: {mean, lo90, hi90} on one set. -> {code,
    reading, next, rests_on, heard (FK-above: the mean at -big or beyond), caveat (FK-above, FK-shut), compression}."""
    if not _iv_ok(d_true) or not _iv_ok(d_blur):
        raise SystemExit("fk_code needs D_true and D_blur, each with a finite mean and 90% interval")
    holds = fk_holds(d_true, d_blur, small, big)
    code = next(c for c in FK_CODES if holds[c])
    row = {c: (w, r, n, o) for c, w, r, n, o in FK_TABLE}[code]
    out = {"code": code, "when": row[0], "reading": row[1], "next": row[2], "rests_on": row[3],
           "compression": COMPRESSION_NOTE}
    if code == "FK-above":
        out["heard"] = d_blur["mean"] <= -big
        if not out["heard"]:
            out["reading"] += " (not by a heard size: the mean is short of -0.10)"
    if code in CAVEAT_CODES:
        out["caveat"] = MEASURE_CAVEAT
    return out


def fk_table_guard():
    """Refuse unless FK_TABLE holds the four codes in order, every line says "not ruled out" where a pass is read and
    never "licensed", each names the number it rests on, FK-above and FK-shut never both hold on a grid of intervals
    (lo < mean < hi), and 0 < SMALL < BIG."""
    if FK_CODES != ("FK-clear", "FK-above", "FK-shut", "FK-undecided"):
        raise SystemExit("FK_TABLE's codes are not the four declared, in order")
    if set(FAVOUR) != set(FK_CODES):
        raise SystemExit("FAVOUR does not order the four codes")
    for c, w, r, n, o in FK_TABLE:
        text = " ".join((w, r, n, o)).lower()
        if "licens" in text:
            raise SystemExit(f"{c}: a code never 'licenses'; a pass reads 'not ruled out'")
        if c in ("FK-clear", "FK-above") and "not ruled out" not in n:
            raise SystemExit(f"{c}: a pass must read 'not ruled out'")
        if not o or not all(q in ("D_true", "D_blur") for q in o.replace(" and ", " ").split()):
            raise SystemExit(f"{c}: names no number it rests on")
    if not 0 < SMALL < BIG:
        raise SystemExit("the thresholds are not 0 < SMALL < BIG")
    grid = [x / 100 for x in range(-30, 31, 1)]
    for lo in grid:
        for m in grid:
            if m <= lo:
                continue
            for hi in grid:
                if hi <= m:
                    continue
                iv = {"mean": m, "lo90": lo, "hi90": hi}
                h = fk_holds(iv, iv)
                if h["FK-above"] and h["FK-shut"]:
                    raise SystemExit(f"FK-above and FK-shut both hold on {iv}")


def park_code(arm_codes):
    """(Pure.) The full row's code from its arms' codes ({arm: code}): the park stands only when every arm reads
    FK-shut; otherwise the more favourable arm's code (clear, above, undecided, shut), said as coming from the full
    row. -> {code, arm, park}."""
    if not arm_codes or any(c not in FK_CODES for c in arm_codes.values()):
        raise SystemExit(f"park_code needs each arm's FK code: {arm_codes}")
    if all(c == "FK-shut" for c in arm_codes.values()):
        return {"code": "FK-shut", "arm": None, "park": True,
                "reading": "the full row confirms FK-shut on both arms: the route is parked (not closed)"}
    arm = min(arm_codes, key=lambda a: (FAVOUR.index(arm_codes[a]), a))
    return {"code": arm_codes[arm], "arm": arm, "park": False,
            "reading": f"from the full row ({arm}): {arm_codes[arm]}; the short row's FK-shut is not confirmed"}


def best_arm(arm_means):
    """(Pure.) A row's best arm: the lowest pooled mean G ({arm: mean}); None when none has one."""
    got = {a: m for a, m in (arm_means or {}).items() if m is not None}
    return min(got, key=lambda a: (got[a], a)) if got else None


def park_lifts(fs_notes_best, codec_best, summarise, small=SMALL):
    """(Pure but for `summarise`.) The park's lift, at zero renders once `fs-notes` is read: per part `fs-notes`' best
    arm's G less the codec's best arm's G ({pkey: G} each, paired on the parts in both); the park lifts (to the user)
    when the paired mean on the pool is at +0.05 or more (the note route 0.05 or more worse than the codec).
    summarise(values) -> {"mean", ...}: the plan's pool, required (`pool_summariser`, BKS+GOAT beside in its row; no
    plain mean over parts). -> {lifts, mean, row, parts}."""
    if not callable(summarise):
        raise SystemExit("park_lifts needs the pool's summariser (pool_summariser(sd, draw)), not a plain mean")
    d = {k: fs_notes_best[k] - codec_best[k] for k in sorted(set(fs_notes_best) & set(codec_best))
         if fs_notes_best[k] is not None and codec_best[k] is not None}
    if not d:
        return {"lifts": False, "mean": None, "row": None, "parts": 0}
    row = summarise(d)
    m = (row or {}).get("mean")
    return {"lifts": m is not None and m >= small, "mean": m, "row": row, "parts": len(d)}


def pool_summariser(sd, draw):
    """The plan's pool for `park_lifts`: `scratch_notes.set_rows`' deciding pool (BKS, GOAT and the panel weighted
    equally), with BKS+GOAT beside. -> summarise(values) -> {mean, lo90, hi90, ..., deciding_sets, bks_goat}."""
    def summarise(values):
        row = SN.set_rows(sd, draw, values) or {}
        return dict(row.get("deciding_pool") or {"mean": None}, deciding_sets=row.get("deciding_sets"),
                    bks_goat=(row.get("bks_goat") or {}).get("all"))
    return summarise


COVERS = {
    "rt-m2l": {"covers": "m2l fed 48 kHz: LOUDAR as released, and anything built in that latent used that way "
                         "(GuitarFlow retrained on m2l included; m2l is Apache-2.0)",
               "does_not_cover": "GuitarFlow as published (SonyCSL weights at 44.1 kHz); m2l fed at its trained "
                                 "44.1 kHz; any other codec",
               "weak_go_means": "LOUDAR's second test may be proposed",
               "park_means": "no LOUDAR download; no rebuild in m2l at 48 kHz"},
    "rt-dac": {"covers": "a rebuild in DAC's latent at 8 kbps: track 3's DAC option, and a codec of EG-VAE's family",
               "does_not_cover": "DAC at fewer codebooks; DAC-VAE itself; any 12-Hz latent",
               "weak_go_means": "track 3 may consider DAC's latent, once fs-notes and its own gate say a guided "
                                "rebuild is wanted",
               "park_means": "track 3 stays in the waveform"},
}


def covers(name):
    """(Pure.) What a codec's code covers and does not, printed with every code."""
    if name not in COVERS:
        raise SystemExit(f"{name!r} has no row (only {list(COVERS)})")
    return dict(COVERS[name], name=name)


# --- the short row's answers (pure) -----------------------------------------------------------------------------------------

def short_answer(rec, dry_sha, checkpoint=CHECKPOINT, budget=BUDGET):
    """(Pure.) A short search record's answer, or why it refuses: the record not refused, its dry guitar the build's,
    exactly `budget` evaluations, `budget_used` = budget, step 1 only, and step 1's incumbent at `checkpoint`, which
    must be "50" (in a short record "100" and "200" equal it and are refused as answers). -> ({select, cp50,
    borrowed: []}, None) or (None, why)."""
    if checkpoint != CHECKPOINT:
        raise SystemExit(f"the short row's answer is checkpoint {CHECKPOINT!r} only, not {checkpoint!r}")
    if "refused" in rec:
        return None, {"search": rec["refused"]}
    if rec.get("dry_sha256") != dry_sha:
        return None, {"dry": "the search record's dry guitar is not the hashed build's"}
    s1 = rec.get("step1") or {}
    if s1.get("evaluations") != budget or len(s1.get("curve") or ()) != budget:
        return None, {"evaluations": f"{s1.get('evaluations')} evaluations, not {budget}"}
    if rec.get("budget_used") != budget or not rec.get("step1_only"):
        return None, {"budget": f"budget_used {rec.get('budget_used')}, step1_only {rec.get('step1_only')}"}
    cp = (s1.get("checkpoints") or {}).get(checkpoint)
    if not cp or not cp.get("settings"):
        return None, {"checkpoint": f"no usable incumbent at {checkpoint}"}
    return {"select": rec["select"], "cp50": cp["settings"], "borrowed": []}, None


def short_answers(parts, recs, dry_shas, search_sha):
    """(Pure but for `search_sha`.) The short row's answers: per part `short_answer`; the refusals reported (S1:
    "stopped" is always False). parts: the draw's; recs: {pkey: record}; dry_shas: {pkey: the build's sha256}. ->
    (answers, refused, stopped)."""
    out, refused = {}, {}
    for p in parts:
        k = p["pkey"]
        a, why = short_answer(recs[k], dry_shas.get(k))
        if why:
            refused[k] = why
            continue
        out[k] = dict(a, search_sha256=search_sha(k))
    return out, refused, S.stopped(refused)


def first_fifty_refusal(full, short, n=BUDGET):
    """(Pure.) Why `answers-full` refuses, or None: on every part the full record's first `n` step-1 values must equal
    the short record's exactly (a part refused in both is skipped). full, short: {pkey: record}."""
    for k in sorted(set(full) | set(short)):
        a, b = full.get(k), short.get(k)
        if a is None or b is None:
            return f"{k}: not in both rows"
        if "refused" in a and "refused" in b:
            continue
        if "refused" in a or "refused" in b:
            return f"{k}: refused in one row only"
        if a["step1"]["curve"][:n] != b["step1"]["curve"] or len(b["step1"]["curve"]) != n:
            return f"{k}: the full row's first {n} evaluations are not the short row's"
    return None


def g50(held):
    """(Pure.) ln(cp50 / Cen) on the held half after `scratch_search.nonfinite_rule` (a non-finite cp50 reads as Cen).
    -> (G50, replaced names)."""
    h, rep = S.nonfinite_rule({"cen": held["cen"], "cp50": held["cp50"]})
    return math.log(h["cp50"] / h["cen"]), rep


def deciding_refusal(rows):
    """(Pure.) The pool rule of `scratch_search.pool_refusal`, on G50, D_true and D_blur: each one's deciding sets must
    be BKS, GOAT and the panel (a lost panel DI file stops the row, to the user), or None."""
    bad = [q for q in rows if (rows.get(q) or {}).get("deciding_sets") != S.DECIDING]
    if bad:
        return f"the deciding pool of {', '.join(bad)} is not {S.DECIDING}: the panel lost a DI file"
    return None


def musdb_train_keys(parts):
    """(Pure.) The panel parts whose song is in MUSDB18's train split (DAC trained on its mix): "BigTroubles -
    Phantom"."""
    return sorted(p["pkey"] for p in parts if p["set"] == "panel"
                  and any(f"/{a}/" in p["cluster"] for a in MUSDB_TRAIN_PANEL))


def report_refusal(rep, name, ans_sha):
    """(Pure.) Why the `-full` commands refuse, or None: the codec's short report must exist, come from the answers
    hashed on main, and read FK-shut on the pool."""
    if rep is None:
        return f"{name}: no short report (run `read --name {name}` first)"
    if rep.get("answers_sha256") != ans_sha:
        return f"{name}: the short report was read from other answers"
    if (rep.get("fk") or {}).get("code") != "FK-shut":
        return f"{name}: the short row reads {(rep.get('fk') or {}).get('code')}, not FK-shut: no full row"
    return None


# --- paths -----------------------------------------------------------------------------------------------------------------

def codec_dir():
    return S.fs_dir() / "codec"


def in_dir():
    return codec_dir() / "in"


def in_json():
    return in_dir() / "in.json"


def out_dir():
    return codec_dir() / "out"


def roundtrip_path(venv):
    return out_dir() / f"roundtrip-{venv}.json"


def rt_path(name, pk):
    return codec_dir() / "rt" / name / f"{pk}.npy"


def build_path():
    return codec_dir() / "build.json"


def figures_path():
    return codec_dir() / "figures.json"


def start_path(name, pk):
    return codec_dir() / "start" / name / f"{pk}.json"


def check_dir():
    return codec_dir() / "check"


def search_path(name, pk, full=False):
    return codec_dir() / ("search-full" if full else "search") / name / f"{pk}.json"


def answers_path(name, full=False):
    return codec_dir() / f"answers{'-full' if full else ''}-{name}.json"


def score_path(name, pk, full=False):
    return codec_dir() / ("score-full" if full else "score") / name / f"{pk}.json"


def rows_path(name, full=False):
    return codec_dir() / f"rows{'-full' if full else ''}-{name}.json"


def report_path(name, full=False):
    return codec_dir() / f"report{'-full' if full else ''}-{name}.json"


# --- the guards ------------------------------------------------------------------------------------------------------------

def codec_keys(entry):
    """(Pure.) The `phase_scratch_codec*` keys of a `preset-ladder` entry."""
    return {k: v for k, v in (entry or {}).items() if k.startswith(KEY_PREFIX)}


def keys_refusal(local, main):
    """(Pure.) Why this checkout's `phase_scratch_codec*` keys are not main's, or None."""
    a, b = codec_keys(local), codec_keys(main)
    if a != b:
        diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
        return f"this checkout's {', '.join(diff)} differ from main's: pull main (run from merged code)"
    return None


def blob_refusal(blob):
    """(Pure.) Why main's `learn/scratch_search.py` is not the one `fs-notes`' checks passed on, or None."""
    if blob != SCRATCH_SEARCH_BLOB:
        return (f"main's learn/scratch_search.py is blob {str(blob)[:12]}, not {SCRATCH_SEARCH_BLOB[:12]}: the shared "
                "path changed: an amendment first")
    return None


def check_refusal(results, shas):
    """(Pure.) Why `fs-notes`' two checks do not stand, or None: both passed (`scratch_notes.checks_passed`) and each
    result file is the one declared (its sha256)."""
    why = SN.checks_passed(results.get("check-score"), results.get("check-search"))
    if why:
        return why
    for kind, want in CHECK_SHA256.items():
        if shas.get(kind) != want:
            return f"{kind}'s result.json is not the one declared ({str(shas.get(kind))[:12]}, not {want[:12]})"
    return None


def _git(*a):
    from learn import pipeline_fix as P

    return subprocess.run(["git", "-C", str(P.REPO), *a], capture_output=True, text=True)


def code_refusal(main):
    """Why this checkout does not run main's codec code, or None: CODE_FILES equal main's, the `phase_scratch_codec*`
    keys equal main's, main's blob of `learn/scratch_search.py` the declared one (`scratch_search.on_main` has fetched
    origin/main and checked `learn/scratch_search.py` and the `phase_fs*` keys)."""
    from learn import note_replay as NR

    for f in CODE_FILES:
        if _git("diff", "--quiet", "origin/main", "--", f).returncode:
            return f"this checkout's {f} differs from main's: run from merged code"
    why = keys_refusal(NR.ledger_entry(), main)
    if why:
        return why
    return blob_refusal(_git("rev-parse", "origin/main:learn/scratch_search.py").stdout.strip())


def require_codec(*phases):
    """Refuse unless this checkout runs main's code and keys, main holds the declarations and `phases`, the shared path
    is the checked one and `fs-notes`' two checks stand. -> main's `preset-ladder` entry."""
    fk_table_guard()
    m = S.require_on_main(S.PHASE, S.PHASE_DRAW, GATE, PHASE, *phases)
    why = code_refusal(m)
    if why:
        raise SystemExit(why)
    res = {k: SN.check_result(k) for k in CHECK_SHA256}
    why = SN.checks_passed(res["check-score"], res["check-search"]) or check_refusal(res, check_shas())
    if why:
        raise SystemExit(why)
    return m


def check_shas():
    """The sha256 of `fs-notes`' two check result files (PF/fs/notes/check-*/result.json), None where missing."""
    out = {}
    for k in CHECK_SHA256:
        p = SN.check_dir(k) / "result.json"
        out[k] = S.file_sha(p) if p.exists() else None
    return out


def require_build(m):
    """build.json, refused unless its sha256 is main's phase_scratch_codec_dry."""
    from learn import note_replay as NR

    if not build_path().exists():
        raise SystemExit("no build (run `build` first)")
    why = NR.hash_refusal(m, PHASE_DRY, S.file_sha(build_path()))
    if why:
        raise SystemExit(f"{why} (the build's hash must be on main before this step)")
    return json.loads(build_path().read_text())


def require_name(name, allowed, build=None):
    if name not in allowed:
        raise SystemExit(f"--name {name!r}: one of {list(allowed)}")
    if build is not None and name not in (build.get("names") or {}):
        raise SystemExit(f"{name}: not in the build ({build.get('dropped')})")


def render_guards(draw, sd):
    """Every render command's: no separation beside, C3r's state the draw's, a render slot."""
    from learn import local_objective as LO
    from learn import note_replay as NR

    NR.no_separation_beside()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    LO._wait_cap()


def disk_guard():
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    if PS.free_gb() < T.DISK_GUARD_GB:
        raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")


def shard_of(parts, shard):
    k, n = shard
    return [p for j, p in enumerate(sorted(parts, key=lambda p: p["pkey"])) if j % n == k]


def load_dry(name, pk, build):
    """The codec's dry guitar, refused unless its sha256 (`npy_sha`, measured from the audio) is the hashed build's.
    -> (float32 audio, sha256)."""
    import numpy as np

    x32 = np.load(rt_path(name, pk)).astype(np.float32)
    sha = S.npy_sha(x32)
    want = build["names"][name][pk]["sha256"]
    if sha != want:
        raise SystemExit(f"{pk}: {name}'s dry guitar is not the hashed build's ({sha[:12]}, not {want[:12]})")
    return x32, sha


# --- the zero-render figures (numpy inside; descriptive, never deciding) ---------------------------------------------------

def logmel(x, n_fft, sr=48000, n_mels=80, fmin=80.0, fmax=10000.0):
    """The log-mel cells (dB) at frames of n_fft, hop n_fft / 4 (`track-codec-ceiling-probes/precheck_probe.py`)."""
    import numpy as np

    hop = n_fft // 4
    w = np.hanning(n_fft)
    n = 1 + (len(x) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(n)[:, None]
    pw = np.abs(np.fft.rfft(x[idx] * w, axis=1)) ** 2
    f = np.fft.rfftfreq(n_fft, 1 / sr)

    def mel(h):
        return 2595 * np.log10(1 + h / 700)
    edges = 700 * (10 ** (np.linspace(mel(fmin), mel(fmax), n_mels + 2) / 2595) - 1)
    fb = np.zeros((n_mels, len(f)))
    for i in range(n_mels):
        a, b, c = edges[i:i + 3]
        fb[i] = np.clip(np.minimum((f - a) / (b - a), (c - f) / (c - b)), 0, None)
    return 10 * np.log10(pw @ fb.T + 1e-20)


def floored(a, b, floor_db=50.0):
    """Mean |a - b| over the cells either side holds, both floored floor_db under a's loudest cell, the mean level
    difference removed."""
    import numpy as np

    fl = a.max() - floor_db
    a2, b2 = np.maximum(a, fl), np.maximum(b, fl)
    keep = (a > fl) | (b > fl)
    d = b2 - a2
    d = d - d[keep].mean()
    return float(np.abs(d[keep]).mean())


def envelope(x, win):
    import numpy as np

    n = len(x) // win
    return np.sqrt((x[:n * win].reshape(n, win) ** 2).mean(1) + 1e-20)


def dry_figures(di, y):
    """The figures of a dry guitar `y` against the true DI `di` (float64, equal length): the floored log-mel distance
    at 256 and 2,048, the 5-ms envelope distance (floored 50 dB under the DI's loudest), the crest change (dB)."""
    import numpy as np

    out = {f"mel{nf}": floored(logmel(di, nf), logmel(y, nf)) for nf in (256, 2048)}
    e1, e2 = 20 * np.log10(envelope(di, 240)), 20 * np.log10(envelope(y, 240))
    fl = e1.max() - 50
    out["env5"] = float(np.abs(np.maximum(e1, fl) - np.maximum(e2, fl)).mean())
    out["crest"] = (20 * math.log10(np.abs(y).max() / np.sqrt((y ** 2).mean()))
                    - 20 * math.log10(np.abs(di).max() / np.sqrt((di ** 2).mean())))
    return out


def band_mask(f, lo=80.0, hi=8000.0):
    return (f >= lo) & (f <= hi)


def spectral_distance(raw, y):
    """Before the measure step: the long-term spectral distance of `y` from `raw` (`di_robustness.smoothed_spectrum`,
    mean absolute dB over 80 Hz to 8 kHz, the in-band level removed). This is what the measure step then removes."""
    import numpy as np

    from learn import di_robustness as DR

    f = np.fft.rfftfreq(DR.N_FFT, 1 / DR.SR)
    m = band_mask(f)
    d = DR.smoothed_spectrum(np.asarray(y, np.float64))[m] - DR.smoothed_spectrum(np.asarray(raw, np.float64))[m]
    return float(np.abs(d - d.mean()).mean())


def balance_offset(y, avg):
    """A measured DI's offset from the average balance (the measure step's ±15 dB clip residual): its smoothed
    spectrum less `avg` (`confirm_run.AVERAGE`), over 80 Hz to 8 kHz with 1/f weights, the weighted mean removed,
    the weighted RMS (dB); as track 4's review measured it (2.7 dB mean, 7.1 max on the true DIs)."""
    import numpy as np

    from learn import di_robustness as DR

    f = np.fft.rfftfreq(DR.N_FFT, 1 / 48000)
    m = band_mask(f)
    w = 1 / f[m]
    w = w / w.sum()
    d = (DR.smoothed_spectrum(np.asarray(y, np.float64)) - avg)[m]
    d = d - (d * w).sum()
    return float(np.sqrt((w * d * d).sum()))


def envelope_lag_ms(di, y, max_ms=50):
    """The lag (ms) of `y` against `di` at the peak of the 1-ms RMS envelopes' cross-correlation (mean removed),
    within ±max_ms; positive: `y` late."""
    import numpy as np

    a, b = np.log(envelope(di, 48)), np.log(envelope(y, 48))
    a, b = a - a.mean(), b - b.mean()
    n = min(len(a), len(b))
    best, lag = None, 0
    for d in range(-max_ms, max_ms + 1):
        v = float(np.dot(a[max(0, -d):n - max(0, d)], b[max(0, d):n - max(0, -d)]))
        if best is None or v > best:
            best, lag = v, d
    return float(lag)


def waveform_lag(di, y, max_lag=2400):
    """The lag (samples) of `y` against `di` at the waveforms' cross-correlation peak, within ±max_lag (beside)."""
    import numpy as np

    n = len(di) + len(y)
    m = 1 << (n - 1).bit_length()
    c = np.fft.irfft(np.fft.rfft(y, m) * np.conj(np.fft.rfft(di, m)), m)
    lags = np.concatenate([np.arange(0, max_lag + 1), np.arange(-max_lag, 0)])
    vals = np.concatenate([c[:max_lag + 1], c[-max_lag:]])
    return int(lags[int(np.argmax(vals))])


def halves_of(x):
    """The two halves of a 492,000-sample section as the judge reads them (TRIM_S, then `pretrain_set.HALVES`)."""
    from learn import pretrain_set as PS

    t = PS.TRIM_S
    return {h: x[int((t + a) * PS.SR):int((t + b) * PS.SR)] for h, (a, b) in PS.HALVES.items()}


def part_figures(di, y):
    """`dry_figures` whole and per half."""
    out = {"whole": dry_figures(di, y)}
    hd, hy = halves_of(di), halves_of(y)
    for h in hd:
        out[h] = dry_figures(hd[h], hy[h])
    return out


# --- prep and build (zero renders) -----------------------------------------------------------------------------------------

def with_next_second(section, longer, n_next=NEXT):
    """(numpy.) The round trip's input: the section exactly as `pretrain_set.section_audio` gives it, then the DI file's
    own next second from a longer read (`longer`, the same start; zeros only where the file ends). The section is kept
    from its own read, so its samples equal `section_audio`'s exactly even where a 44.1-kHz file's resampling edge
    differs between the two reads. -> (float32 array of len(section) + n_next, the real samples after the section)."""
    import numpy as np

    n = len(section)
    tail = np.asarray(longer[n:n + n_next], np.float32)
    real = len(tail)
    return np.concatenate([np.asarray(section, np.float32), np.pad(tail, (0, n_next - real))]), real


def longer_read(path, start_s):
    """`pretrain_set.section_audio`'s read made one second longer (zeros before where the file starts later)."""
    import numpy as np

    from learn import pretrain_set as PS

    a = start_s - PS.TRIM_S
    dur = PS.SEC_S + PS.TRIM_S + NEXT / PS.SR
    x = PS.load_mono(path, PS.SR, max(0.0, a), dur - max(0.0, -a))
    if a < 0:
        x = np.concatenate([np.zeros(int(round(-a * PS.SR)), np.float32), x])
    return x


def cmd_prep(_args):
    """Per part the raw section and the DI file's next second (`with_next_second`) to in/<pkey>.npy, its first
    SECTION samples asserted equal to `pretrain_set.section_audio`; in.json with each sha256 and the draw's."""
    require_codec()
    import numpy as np

    from learn import note_replay as NR
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    never_overwrite_all([in_json()])
    draw = S.require_draw()
    sd = NR.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    parts = {}
    for p in draw["parts"]:
        k = p["pkey"]
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        sec = PS.section_audio(prt["di_path"], prt["start_s"])
        if len(sec) != SECTION:
            raise SystemExit(f"{k}: the section has {len(sec)} samples, not {SECTION}")
        x, real = with_next_second(sec, longer_read(prt["di_path"], prt["start_s"]))
        if not np.array_equal(x[:SECTION], sec) or len(x) != IN_LEN or not np.isfinite(x).all():
            raise SystemExit(f"{k}: the input's section is not section_audio's")
        out = in_dir() / f"{k}.npy"
        S.never_overwrite(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        np.save(out, x)
        parts[k] = {"sha256": S.file_sha(out), "section_sha256": S.npy_sha(sec), "next_real": real}
    P.save(in_json(), {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "sr": PS.SR, "n": IN_LEN, "section": SECTION,
                       "draw_sha256": S.file_sha(S.draw_path()), "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                       "next_real_parts": sum(v["next_real"] > 0 for v in parts.values()), "parts": parts})
    print(f"CODEC PREP: {len(parts)} parts; {sum(v['next_real'] == NEXT for v in parts.values())} with a full next "
          f"second of real audio, the rest zero-padded where the file ends")


def never_overwrite_all(paths):
    for q in paths:
        S.never_overwrite(q)


def timing_stop(offsets, tol=TIMING_MS, stop=TIMING_STOP):
    """(Pure.) The build's timing check: {name: {pkey: lag ms}} -> ({name: [pkeys beyond tol]}, stopped)."""
    beyond = {n: sorted(k for k, v in d.items() if v is None or abs(v) > tol) for n, d in offsets.items()}
    return beyond, any(len(v) >= stop for v in beyond.values())


def lufs_beyond(values, target=LUFS, tol=LUFS_TOL):
    """(Pure.) The build's level check: {name: {pkey: integrated LUFS}} -> [(name, pkey, LUFS)] more than `tol` from
    `target`. The tolerance is 0.25 LU, not 0.05: pyloudnorm's gating after `to_lufs`' single gain leaves the true DI
    itself up to 0.121 LU off -22.9 on 3 of the 47 parts (byte-equal to `note_replay.di_section`), and a codec output's
    low-level blocks fall across the gate on their own, so they need not shift with the true DI's; a missed measure step
    sits about 12 LU off (the raw sections are near -35 LUFS)."""
    return sorted((n, k, v) for n, d in values.items() for k, v in d.items()
                  if v is None or not math.isfinite(v) or abs(v - target) > tol)


def cmd_build(_args):
    """Per name and part: `song_bank.measure` of the round trip as float32. Every check runs before anything is
    written: finite, SECTION samples, the level (`lufs_beyond`, every value recorded with the true DI's beside),
    `rt-id`'s sha256 equal to the true DI's (`note_replay.di_section`) on all 47, the timing offset (1-ms envelope; the
    waveform's peak beside) within 1 ms with 3 or more parts beyond it stopping the build. A refusal writes only
    build-stopped-<time>.json (every value) and no rt/ file. Otherwise rt/<name>/<pkey>.npy, figures.json (zero-render
    figures, descriptive) and build.json; build.json's sha256 is printed for phase_scratch_codec_dry. A venv whose
    roundtrip record is missing is reported as dropped."""
    require_codec()
    import numpy as np

    from learn import confirm_run as CR
    from learn import direc_check as DC
    from learn import note_replay as NR
    from learn import pipeline_fix as P
    from learn import song_bank as SB

    never_overwrite_all([build_path(), figures_path()])
    draw = S.require_draw()
    sd = NR.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    in_rec = json.loads(in_json().read_text())
    if in_rec["draw_sha256"] != S.file_sha(S.draw_path()):
        raise SystemExit("in.json was made from another draw")
    rts = {v: json.loads(roundtrip_path(v).read_text()) for v in ("codec", "dac") if roundtrip_path(v).exists()}
    if "codec" not in rts:
        raise SystemExit("no codec-venv round trip (roundtrip-codec.json): rt-m2l and rt-id are needed")
    for v, r in rts.items():
        if r["in_json_sha256"] != S.file_sha(in_json()):
            raise SystemExit(f"roundtrip-{v}.json was made from another in.json")
    names = [n for n in NAMES if VENV_OF[n] in rts and n in rts[VENV_OF[n]]["codecs"]]
    dropped = [n for n in NAMES if n not in names]
    if "rt-m2l" not in names or "rt-id" not in names:
        raise SystemExit(f"the build needs rt-m2l and rt-id (got {names})")
    for n in names:
        for p in draw["parts"]:
            S.never_overwrite(rt_path(n, p["pkey"]))
    blur = json.loads((NR.replay_dir() / "blur.json").read_text())
    if blur["draw_sha256"] != draw["replay_draw_sha256"]:
        raise SystemExit("blur.json was made from another replay draw")
    rby = {p["pkey"]: p for p in NR.require_draw()["parts"]}
    avg = np.load(CR.AVERAGE)
    import pyloudnorm

    meter = pyloudnorm.Meter(DC.SR)
    shas = {n: {} for n in names}
    lufs = {n: {} for n in names}
    true_lufs = {}
    held = {}                                          # (name, pkey) -> the measured DI, written only after every check
    figs = {"parts": {}}
    offsets = {n: {} for n in names if n != "rt-id"}
    bad = []
    for p in draw["parts"]:
        k = p["pkey"]
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        di32 = NR.di_section(prt)
        di = np.asarray(di32, np.float64)
        true_lufs[k] = float(meter.integrated_loudness(di))
        raw = np.load(in_dir() / f"{k}.npy").astype(np.float64)[:SECTION]
        am = np.asarray(NR.load_dry("avg+mild", rby[k], di32, blur), np.float64)
        pf = {"true": {"balance_offset": balance_offset(di, avg), "lufs": true_lufs[k]},
              "avg+mild": {"vs_true": part_figures(di, am), "balance_offset": balance_offset(am, avg)}}
        meas = {}
        for n in names:
            src = out_dir() / n / f"{k}.npy"
            y_raw = np.load(src)
            if S.file_sha(src) != rts[VENV_OF[n]]["parts"][n][k]["sha256"]:
                raise SystemExit(f"{src}: not the file its round trip wrote")
            if len(y_raw) != SECTION or not np.isfinite(y_raw).all():
                raise SystemExit(f"{n} {k}: {len(y_raw)} samples or non-finite")
            y = SB.measure(np.asarray(y_raw, np.float64)).astype(np.float32)
            if len(y) != SECTION or not np.isfinite(y).all():
                raise SystemExit(f"{n} {k}: the measured DI is not finite or not {SECTION} samples")
            sha = S.npy_sha(y)
            lufs[n][k] = float(meter.integrated_loudness(np.asarray(y, np.float64)))
            shas[n][k] = {"sha256": sha, "n": len(y), "lufs": lufs[n][k], "true_lufs": true_lufs[k]}
            held[(n, k)] = y
            meas[n] = np.asarray(y, np.float64)
            if n == "rt-id":
                if sha != S.npy_sha(di32):
                    bad.append(k)
                continue
            pf[n] = {"vs_true": part_figures(di, meas[n]), "before_measure": spectral_distance(raw, y_raw),
                     "balance_offset": balance_offset(meas[n], avg), "lufs": lufs[n][k],
                     "lag_ms": envelope_lag_ms(di, meas[n]), "lag_samples": waveform_lag(di, meas[n])}
            offsets[n][k] = pf[n]["lag_ms"]
        if "rt-m2l" in meas and "rt-m2l-b" in meas:
            pf["rt-m2l-b"]["vs_rt_m2l"] = part_figures(meas["rt-m2l"], meas["rt-m2l-b"])
        figs["parts"][k] = pf
        print(f"{k[-50:]}: true {true_lufs[k]:.3f}; " + ", ".join(f"{n} {lufs[n][k]:.3f} LUFS" for n in names),
              flush=True)
    beyond, stop = timing_stop(offsets)
    off_level = lufs_beyond(lufs)
    rec = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "draw_sha256": S.file_sha(S.draw_path()),
           "in_json_sha256": S.file_sha(in_json()),
           "roundtrip_sha256": {v: S.file_sha(roundtrip_path(v)) for v in rts},
           "manifest_sha256": {v: r["manifest_sha256"] for v, r in rts.items()},
           "seconds_a_part": {v: r["seconds_a_part"] for v, r in rts.items()},
           "dropped": dropped, "rt_id_equal": len(draw["parts"]) - len(bad), "rt_id_unequal": bad,
           "lufs_target": LUFS, "lufs_tol": LUFS_TOL, "true_lufs": true_lufs, "lufs_beyond": off_level,
           "timing_beyond_1ms": beyond, "timing_stopped": stop, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
           "names": shas}
    why = []
    if bad:
        why.append(f"rt-id is not the true DI byte for byte on {len(bad)} parts: the build wraps more than the codec")
    if off_level:
        why.append(f"{len(off_level)} measured DIs more than {LUFS_TOL} LU off {LUFS}: {off_level[:3]}")
    if stop:
        why.append(f"the timing check: {beyond} (3 or more parts beyond 1 ms)")
    if why:                                            # nothing under rt/ is written: a rerun is not blocked
        P.save(codec_dir() / f"build-stopped-{time.strftime('%Y%m%d-%H%M%S')}.json", dict(rec, stopped=why))
        raise SystemExit("the build stops: " + "; ".join(why))
    for (n, k), y in held.items():
        out = rt_path(n, k)
        S.never_overwrite(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        np.save(out, y)
        if S.file_sha(out) != shas[n][k]["sha256"]:
            raise SystemExit(f"{out}: the file's sha256 is not npy_sha's")
    figs["summary"] = figure_rows(sd, draw, figs["parts"], [n for n in names if n != "rt-id"])
    P.save(figures_path(), dict(figs, plan=PLAN, time=time.strftime("%Y-%m-%d %H:%M:%S"),
                                anchors_avg_mild={"mel256": 2.49, "mel2048": 3.05, "env5": 2.00, "crest": -0.69}))
    rec["figures_sha256"] = S.file_sha(figures_path())
    P.save(build_path(), rec)
    print(f"CODEC BUILD: {', '.join(names)} on {len(draw['parts'])} parts (dropped {dropped}); rt-id equal on "
          f"{rec['rt_id_equal']}; level within {LUFS_TOL} LU on all; timing beyond 1 ms {beyond}; sha256 "
          f"{S.file_sha(build_path())} (into the ledger as {PHASE_DRY} before any render)")


def figure_rows(sd, draw, parts, names):
    """The figures' summaries: per dry guitar and figure, the mean over parts and the paired difference against
    avg+mild's by `scratch_notes.set_rows` (the pool and BKS+GOAT)."""
    out = {}
    for n in names:
        res = {}
        for f in ("mel256", "mel2048", "env5", "crest"):
            for h in ("whole", "A", "B"):
                v = {k: pf[n]["vs_true"][h][f] for k, pf in parts.items() if n in pf}
                a = {k: pf["avg+mild"]["vs_true"][h][f] for k, pf in parts.items()}
                d = {k: v[k] - a[k] for k in v}
                rd = SN.set_rows(sd, draw, d)
                res[f"{f}_{h}"] = {"mean": sum(v.values()) / len(v), "less_avg_mild_pool": (rd or {}).get(
                    "deciding_pool"), "less_avg_mild_bks_goat": ((rd or {}).get("bks_goat") or {}).get("all")}
        for f in ("before_measure", "balance_offset", "lag_ms"):
            v = [pf[n][f] for pf in parts.values() if n in pf]
            res[f] = {"mean": sum(v) / len(v), "max": max(v), "min": min(v)}
        out[n] = res
    v = [pf["true"]["balance_offset"] for pf in parts.values()]
    out["true"] = {"balance_offset": {"mean": sum(v) / len(v), "max": max(v)}}
    v = [pf["avg+mild"]["balance_offset"] for pf in parts.values()]
    out["avg+mild"] = {"balance_offset": {"mean": sum(v) / len(v), "max": max(v)},
                       **{f: sum(pf["avg+mild"]["vs_true"]["whole"][f] for pf in parts.values()) / len(parts)
                          for f in ("mel256", "mel2048", "env5", "crest")}}
    return out


# --- the start reads and the control (renders) -----------------------------------------------------------------------------

def start_value(p, name, x32, ref_blank, new_renderer, path, dry_sha):
    """The start value for a part and dry guitar: `scratch_notes.first_evaluation(p)` (step 1's exact first evaluation)
    through the dry guitar in its own fresh primed process (2 renders), judged on the search half against the reference
    zeroed outside it, as `run_part` judges; written once (an existing file for the same dry guitar is the value).
    Refuses a part whose first evaluation is not `run_part`'s priming `sx1(start)`. -> (value, renders)."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import full_controls as F
    from learn import local_objective as LO
    from learn import note_replay as NR
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS

    if path.exists():
        rec = json.loads(path.read_text())
        if rec["dry_sha256"] != dry_sha:
            raise SystemExit(f"{path.name}: a start value for another dry guitar")
        return rec["value"], 0
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    dj = np.asarray(x32, np.float64)[trim[0]:trim[1]]
    xs = SN.first_evaluation(p)
    if xs != LO.tdict(LO.sdict(F.c1a_start(p["cen"]["settings"], p["amp"]))):
        raise SystemExit(f"{p['pkey']}: the first evaluation is not run_part's priming sx1(start): an amendment first")
    y = np.asarray(AM.fresh_render(new_renderer, x32, p["cen"]["select"], xs, xs), np.float64)[trim[0]:trim[1]]
    v = NR.half_distance(ref_blank, y, dj, p["lag"], p["search"]) if np.isfinite(y).all() else math.inf
    P.save(path, {"plan": PLAN, "part": p["pkey"], "dry": name, "dry_sha256": dry_sha, "value": v,
                  "start_read": math.log(v / p["start_ref"]["true"][REF]) if S.finite_pos(v) else None,
                  "render_sha256": AM.audio_sha(np.nan_to_num(y)), "renders": 2,
                  "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    return v, 2


def cmd_start(args):
    """The start reads (2 renders a part): `start_value` for `--name` (rt-m2l, rt-m2l-b, rt-dac on all 47; rt-id on
    the 2 check parts only). -> start/<name>/<pkey>.json."""
    m = require_codec(PHASE_DRY)
    build = require_build(m)
    require_name(args.name, START_NAMES, build)
    from learn import cc_build as CB
    from learn import note_replay as NR

    draw = S.require_draw()
    sd = NR.Stored()
    render_guards(draw, sd)
    parts = draw["parts"]
    if args.name == "rt-id":
        keep = set(SN.check_parts(parts))
        parts = [p for p in parts if p["pkey"] in keep]
    total, t0 = 0, time.time()
    for p in shard_of(parts, args.shard):
        if start_path(args.name, p["pkey"]).exists():
            continue
        disk_guard()
        x32, sha = load_dry(args.name, p["pkey"], build)
        v, used = start_value(p, args.name, x32, S.load_ref_blank(sd, p, REF), CB.new_renderer,
                              start_path(args.name, p["pkey"]), sha)
        total += used
        print(f"{p['pkey'][-60:]}: start {v:.5g} (true DI {p['start_ref']['true'][REF]:.5g}); {total} renders, "
              f"{time.time() - t0:.0f} s", flush=True)
    print(f"CODEC START DONE {args.name} {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s")


def short_search(p, name, x32, sha, ref_blank, new_renderer, lists, start_ref, budget=BUDGET):
    """This module's search path: the dry guitar's sha256 measured from the audio handed over (refused before any
    render unless it is `sha`), then `scratch_search.run_part(budget, step1_only=True)` with the start value as the
    start check's reference; `budget_used` recorded (run_part writes its own `budget: 200`)."""
    got = S.npy_sha(x32)
    if got != sha:
        raise SystemExit(f"{p['pkey']}: the dry guitar handed to the search is not the declared one ({got[:12]}, not "
                         f"{sha[:12]}): nothing rendered")
    rec = S.run_part(p, name, REF, x32, ref_blank, new_renderer, lists, budget=budget, start_ref=start_ref,
                     dry_sha256=got, step1_only=True)
    rec["budget_used"] = budget
    return rec


def cmd_control(_args):
    """The controls (22 renders), once: `rt-id` on the 2 check parts through `short_search` at a budget of 10, its
    evaluations equal to the start of row (b)'s stored step-1 curve exactly (`scratch_notes.search_check_verdict`);
    and each `rt-id` start value within START_TOL of the draw's true-DI value. -> check/result.json."""
    m = require_codec(PHASE_DRY)
    build = require_build(m)
    S.never_overwrite(check_dir() / "result.json")
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import note_replay as NR
    from learn import pipeline_fix as P

    draw = S.require_draw()
    sd = NR.Stored()
    render_guards(draw, sd)
    by = {p["pkey"]: p for p in draw["parts"]}
    lists = C.mic_lists()
    new, stored, starts, total = {}, {}, {}, 0
    for k in SN.check_parts(draw["parts"]):
        p = by[k]
        sp = start_path("rt-id", k)
        if not sp.exists():
            raise SystemExit(f"{k}: no rt-id start value (run `start --name rt-id` first)")
        x32, sha = load_dry("rt-id", k, build)
        v = json.loads(sp.read_text())
        if v["dry_sha256"] != sha:
            raise SystemExit(f"{k}: the rt-id start value is for another dry guitar")
        starts[k] = {"value": v["value"], "true_di": p["start_ref"]["true"][REF],
                     "ok": S.start_check(v["value"], p["start_ref"]["true"][REF])}
        out = check_dir() / f"{k}.json"
        S.never_overwrite(out)
        rec = short_search(p, "rt-id", x32, sha, S.load_ref_blank(sd, p, REF), CB.new_renderer, lists, v["value"],
                           budget=CONTROL_BUDGET)
        total += rec.get("renders", 0)
        P.save(out, rec)
        new[k], stored[k] = rec, json.loads(S.search_path(STEM_ROW, k).read_text())
    verdict = SN.search_check_verdict(new, stored)
    res = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "renders": total, "budget": CONTROL_BUDGET,
           "search": verdict, "start": starts,
           "passed": verdict["passed"] and all(s["ok"] for s in starts.values()),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(check_dir() / "result.json", res)
    print(f"CODEC CONTROL {'PASS' if res['passed'] else 'FAIL'}: {total} renders; search {verdict['mismatches']}; "
          f"start {json.dumps({k[-40:]: s['ok'] for k, s in starts.items()})}")


def control_refusal(res):
    """(Pure.) Why `search` refuses on the control, or None."""
    if res is None:
        return "the control has not run (run `control` first)"
    if not res.get("passed"):
        return f"the control did not pass: {res.get('search')} {res.get('start')}"
    return None


def require_control():
    p = check_dir() / "result.json"
    why = control_refusal(json.loads(p.read_text()) if p.exists() else None)
    if why:
        raise SystemExit(why)


# --- the short row: search, answers, score, read ---------------------------------------------------------------------------

def start_ref_of(name, pk, sha):
    sp = start_path(name, pk)
    if not sp.exists():
        raise SystemExit(f"{pk}: no {name} start value (run `start --name {name}` first)")
    v = json.loads(sp.read_text())
    if v["dry_sha256"] != sha:
        raise SystemExit(f"{pk}: the {name} start value is for another dry guitar")
    return v["value"]


def cmd_search(args):
    """One shard of a codec's short searches (51 renders a part): the hashed dry guitar, `short_search` at a budget of
    50 against `xlnoG@-3` zeroed outside the search half; `ledger` and `budget_used: 50` added; saved once."""
    m = require_codec(PHASE_DRY)
    build = require_build(m)
    require_name(args.name, SEARCHED, build)
    require_control()
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import note_replay as NR
    from learn import pipeline_fix as P

    draw = S.require_draw()
    sd = NR.Stored()
    render_guards(draw, sd)
    mine = shard_of(draw["parts"], args.shard)
    if args.first:
        mine = mine[:args.first]
    lists = C.mic_lists()
    total, t0 = 0, time.time()
    for p in mine:
        out = search_path(args.name, p["pkey"])
        if out.exists():
            continue
        disk_guard()
        x32, sha = load_dry(args.name, p["pkey"], build)
        rec = short_search(p, args.name, x32, sha, S.load_ref_blank(sd, p, REF), CB.new_renderer, lists,
                           start_ref_of(args.name, p["pkey"], sha))
        rec["ledger"] = f"{LEDGER_ID} {PHASE}"
        S.never_overwrite(out)
        P.save(out, rec)
        total += rec.get("renders", 0)
        if "refused" in rec:
            print(f"{p['pkey'][-60:]}: REFUSED {rec['refused']}", flush=True)
        print(f"shard {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s "
              f"({total / max(1, time.time() - t0) * 3600:.0f} an hour)", flush=True)
    print(f"FS-CODEC SEARCH DONE {args.name} {args.shard[0]}/{args.shard[1]}: {total} renders in "
          f"{time.time() - t0:.0f} s")


def cmd_answers(args):
    """A codec's short answers (zero renders): `short_answers` on its 47 search records (the hashed build's dry
    guitar, 50 evaluations, checkpoint "50" only), the refusal stop at 3. -> answers-<name>.json; its sha256 into the
    ledger as phase_scratch_codec_answers_<m2l or dac> before `score`."""
    m = require_codec(PHASE_DRY)
    build = require_build(m)
    require_name(args.name, SEARCHED, build)
    S.never_overwrite(answers_path(args.name))
    from learn import pipeline_fix as P

    draw = S.require_draw()
    recs = {}
    for p in draw["parts"]:
        sp = search_path(args.name, p["pkey"])
        if not sp.exists():
            raise SystemExit(f"{p['pkey']}: not searched")
        recs[p["pkey"]] = json.loads(sp.read_text())
    shas = {k: v["sha256"] for k, v in build["names"][args.name].items()}
    parts, refused, stop = short_answers(draw["parts"], recs, shas, lambda k: S.file_sha(search_path(args.name, k)))
    out = {"plan": PLAN, "row": ROW, "dry": args.name, "ref": S.REF_NAME[REF], "checkpoint": CHECKPOINT,
           "draw_sha256": S.file_sha(S.draw_path()), "build_sha256": S.file_sha(build_path()),
           "time": time.strftime("%Y-%m-%d %H:%M:%S"), "renders": sum(r.get("renders", 0) for r in recs.values()),
           "refused": refused, "stopped": stop, "parts": parts}
    P.save(answers_path(args.name), out)
    print(f"FS-CODEC ANSWERS {args.name}: {len(parts)} parts, {len(refused)} refused (each reads at Cen); "
          f"{out['renders']} search renders; sha256 {S.file_sha(answers_path(args.name))} (into the ledger as "
          f"{phase_answers(args.name)} before `score`)")


def require_answers(m, name, full=False):
    from learn import note_replay as NR

    p = answers_path(name, full)
    if not p.exists():
        raise SystemExit(f"no answers for {name} (run `answers{'-full' if full else ''}` first)")
    why = NR.hash_refusal(m, phase_answers(name, full), S.file_sha(p))
    if why:
        raise SystemExit(f"{why} (the hash must be on main before this step)")
    return json.loads(p.read_text())


def score_shard(args, full):
    m = require_codec(PHASE_DRY, phase_answers(args.name, full))
    require_build(m)
    require_name(args.name, SEARCHED)
    if full:
        require_shut(m, args.name)
    ans = require_answers(m, args.name, full)
    if ans.get("stopped"):                               # no answers file is written stopped since S1
        raise SystemExit(f"{args.name}'s answers were written stopped: nothing is scored")
    from learn import cc_build as CB
    from learn import note_replay as NR
    from learn import pipeline_fix as P

    draw = S.require_draw()
    sd = NR.Stored()
    render_guards(draw, sd)
    sha = S.file_sha(answers_path(args.name, full))
    total, t0 = 0, time.time()
    for p in shard_of(draw["parts"], args.shard):
        out = score_path(args.name, p["pkey"], full)
        a = ans["parts"].get(p["pkey"])
        if a is None or out.exists():
            continue
        disk_guard()
        rec, used = S.score_row_part(p, a, ans["parts"], ROW, sha, sd, CB.new_renderer)
        total += used
        P.save(out, rec)
        print(f"{p['pkey'][-60:]}: scored {rec['distinct_renders']} settings; scoring control "
              f"{'ok' if rec['scoring_control_ok'] else 'MISS'}; {total} renders, {time.time() - t0:.0f} s", flush=True)
    print(f"FS-CODEC SCORE{' FULL' if full else ''} DONE {args.name} {args.shard[0]}/{args.shard[1]}: {total} renders "
          f"in {time.time() - t0:.0f} s")


def cmd_score(args):
    """One shard of a codec's short score (4 renders a part): `scratch_search.score_row_part` on the hashed answers
    ({select, cp50, borrowed: []}: Cen and cp50 through the true DI on the held half, the scoring control)."""
    score_shard(args, False)


def codec_g50(draw, ans, answers_sha, score_file):
    """The short row's per-part G50 from its score files: each from these answers, the scoring control passed,
    `g50`'s non-finite rule. -> (per {pkey: G50 or None}, refused, replaced, control misses)."""
    refused = dict(ans["refused"])
    per, replaced, miss = {}, {}, []
    for p in draw["parts"]:
        k = p["pkey"]
        if ans.get("stopped") or k not in ans["parts"]:
            per[k] = None
            continue
        sp = score_file(k)
        if not sp.exists():
            raise SystemExit(f"{k}: not scored")
        sc = json.loads(sp.read_text())
        if sc["answers_sha256"] != answers_sha:
            raise SystemExit(f"{k}: scored from other answers")
        if not sc["scoring_control_ok"]:                 # S1: a miss is rerun once in a fresh process first
            rp = S.rerun_path(sp)
            if not rp.exists():
                raise SystemExit(f"{k}: a scoring-control miss not yet rerun once in a fresh process: run `score "
                                 "--rerun` first")
            again = json.loads(rp.read_text())
            if again["scoring_control_ok"] and again["answers_sha256"] == answers_sha:
                sc = again
        if not sc["scoring_control_ok"]:
            refused[k] = {"scoring_control": {"cen": sc["held"]["cen"], "stored": sc["cen_stored"]}}
            miss.append(k)
            per[k] = None
            continue
        per[k], rep = g50(sc["held"])
        if rep:
            replaced[k] = rep
    return per, refused, replaced, miss


def comparator_g50(draw, ans, answers_sha, score_file):
    """A comparator row's (b or c) per-part G50 and final-answer G from its stored score files: each from its hashed
    answers, the scoring control passed, held["cp50"] and held["cen"] by `g50`. -> ({pkey: G50}, {pkey: G})."""
    g, ga = {}, {}
    for p in draw["parts"]:
        k = p["pkey"]
        if k not in ans["parts"]:
            continue
        sc = json.loads(score_file(k).read_text())
        if sc["answers_sha256"] != answers_sha:
            raise SystemExit(f"{k}: the comparator was scored from other answers")
        if not sc["scoring_control_ok"]:
            continue
        g[k] = g50(sc["held"])[0]
        ga[k] = math.log(sc["held"]["answer"] / sc["held"]["cen"]) if S.finite_pos(sc["held"].get("answer")) else None
    return g, ga


def comparators():
    """Rows (b) and (c): their answers by `scratch_search.require_hash` (main's phase_fs_answers_stem and _both) and
    their per-part G50 and G. -> {row: (G50, G)}."""
    draw = S.require_draw()
    out = {}
    for row in (STEM_ROW, BOTH_ROW):
        ans = S.require_hash(S.phase_answers(row), S.answers_path(row))
        out[row] = comparator_g50(draw, ans, S.file_sha(S.answers_path(row)), lambda k, r=row: S.score_path(r, k))
    return out


def paired(a, b):
    """(Pure.) a - b per part where both hold a value."""
    return {k: a[k] - b[k] for k in a if a.get(k) is not None and b.get(k) is not None}


def pool_of_sets(row):
    """BKS, GOAT and the panel pooled (`full_controls_c3r.pooled`) from a summary's set rows, whatever the panel's DI
    files (beside only: `summarise` itself falls back to BKS+GOAT under 3)."""
    from learn import full_controls_c3r as R

    rows = {s: (row or {}).get(s) or {} for s in S.DECIDING}
    return R.pooled(rows) if all(v.get("mean") is not None for v in rows.values()) else None


def read_short_rows(sd, draw, per, comp, figs=None, starts=None, recs=None, name=None):
    """The short row's numbers: G50, D_true, D_blur on the pool and BKS+GOAT (`scratch_notes.set_rows`), and the
    beside readings. per: {pkey: G50 or None}; comp: {row: (G50, G)}. -> rows."""
    g = {k: v for k, v in per.items() if v is not None}
    gb, gc = comp[STEM_ROW][0], comp[BOTH_ROW][0]
    d_true, d_blur = paired(g, gb), paired(g, gc)
    rows = {"G50": SN.set_rows(sd, draw, g), "D_true": SN.set_rows(sd, draw, d_true),
            "D_blur": SN.set_rows(sd, draw, d_blur)}
    gbr = SN.set_rows(sd, draw, {k: gb[k] for k in g if k in gb})
    beside = {"compression": COMPRESSION, "compression_note": COMPRESSION_NOTE, "measure_caveat": MEASURE_CAVEAT,
              "share_of_row_b_g50_kept": {
                  "pool": SN.share_of((rows["G50"] or {}).get("deciding_pool"), (gbr or {}).get("deciding_pool")),
                  "bks_goat": SN.share_of(((rows["G50"] or {}).get("bks_goat") or {}).get("all"),
                                          ((gbr or {}).get("bks_goat") or {}).get("all"))},
              "g50_rows_b_c": {r: (SN.set_rows(sd, draw, comp[r][0]) or {}).get("deciding_pool")
                               for r in (STEM_ROW, BOTH_ROW)},
              "parts_at_or_over_0.10": sorted(k for k, v in g.items() if v >= BIG)}
    if name == "rt-dac":
        out = set(musdb_train_keys(draw["parts"]))
        keep = {k for k in g if k not in out}
        beside["without_musdb_train"] = {
            "left_out": sorted(out), "note": "the panel on its two other DI files (pooled by full_controls_c3r.pooled)",
            **{q: pool_of_sets(SN.set_rows(sd, draw, v, keep)) for q, v in (("D_true", d_true), ("D_blur", d_blur))}}
    if figs:
        res = {k: (figs["parts"].get(k) or {}).get("true", {}).get("balance_offset") for k in d_blur}
        beside["d_blur_vs_true_clip_residual_spearman"] = SN.spearman(
            [(res[k], d_blur[k]) for k in d_blur if res.get(k) is not None])
        sp = {}
        for f in ("mel256", "mel2048", "env5", "crest"):
            sp[f] = SN.spearman([(figs["parts"][k][name]["vs_true"]["whole"][f], d_true[k]) for k in d_true
                                 if name in figs["parts"].get(k, {})])
        sp["before_measure"] = SN.spearman([(figs["parts"][k][name]["before_measure"], d_true[k]) for k in d_true
                                            if name in figs["parts"].get(k, {})])
        beside["d_true_vs_figures_spearman"] = sp
    if starts:
        sr = {k: v for k, v in starts.items() if v is not None}
        beside["start_read"] = {"mean": sum(sr.values()) / len(sr) if sr else None,
                                "d_true_spearman": SN.spearman([(sr[k], d_true[k]) for k in d_true if k in sr])}
    if recs:
        gain = {}
        for k, r in recs.items():
            cp = ((r.get("step1") or {}).get("checkpoints") or {}).get(CHECKPOINT)
            c = (r.get("step1") or {}).get("curve") or []
            if cp and c and S.finite_pos(cp.get("value")) and S.finite_pos(c[0]):
                gain[k] = math.log(cp["value"] / c[0])
        pairs = [(gain[k], g[k]) for k in gain if k in g]
        beside["search_gain_vs_held_g50"] = {"pearson": SN._pearson(pairs), "spearman": SN.spearman(pairs)}
    rows["beside"] = beside
    return rows


def cmd_read(args):
    """A codec's short reading (zero renders), once: per part G50 (`codec_g50`), rows (b) and (c)'s G50 from their
    hashed answers (`comparators`), D_true and D_blur on the pool and BKS+GOAT, the pool rule, the rows saved before
    the code; then `fk_code` on the pool (and on BKS+GOAT beside), with `covers`, the compression note and the measure
    caveat. -> rows-<name>.json, report-<name>.json (`next: "full row"` on FK-shut)."""
    m = require_codec(PHASE_DRY, phase_answers(args.name))
    require_build(m)
    require_name(args.name, SEARCHED)
    ans = require_answers(m, args.name)
    never_overwrite_all([rows_path(args.name), report_path(args.name)])
    from learn import note_replay as NR
    from learn import pipeline_fix as P

    draw = S.require_draw()
    sd = NR.Stored()
    sha = S.file_sha(answers_path(args.name))
    per, refused, replaced, miss = codec_g50(draw, ans, sha, lambda k: score_path(args.name, k))
    out = {"plan": PLAN, "row": ROW, "name": args.name, "answers_sha256": sha, "refused": refused,
           "stopped": S.stopped(refused), "nonfinite_replaced": replaced, "scoring_control_misses": miss,
           "covers": covers(args.name), "time": time.strftime("%Y-%m-%d %H:%M:%S"), "parts": per,
           "refusal_report": S.refusal_report(refused, {p["pkey"]: p["set"] for p in draw["parts"]}, S.DECIDING)}
    passing = per
    per = S.itt_values(per, refused)                    # S1: the deciding read on every part, a refused one at Cen
    figs = json.loads(figures_path().read_text()) if figures_path().exists() else None
    starts = {p["pkey"]: (json.loads(start_path(args.name, p["pkey"]).read_text()).get("start_read")
                          if start_path(args.name, p["pkey"]).exists() else None) for p in draw["parts"]}
    recs = {p["pkey"]: json.loads(search_path(args.name, p["pkey"]).read_text()) for p in draw["parts"]}
    rows = read_short_rows(sd, draw, per, comparators(), figs, starts, recs, args.name)
    rows_pass = read_short_rows(sd, draw, passing, comparators(), figs, starts, recs, args.name) if refused else rows
    P.save(rows_path(args.name), dict(out, rows=rows, rows_passing_only=rows_pass))   # saved before the code
    why = deciding_refusal({q: rows[q] for q in ("G50", "D_true", "D_blur")})
    if why:
        P.save(report_path(args.name), dict(out, rows=rows, fk=None, stopped=True, stop_reason=why))
        print(f"{args.name}: STOPPED ({why}); to the user")
        return
    fk = fk_code(rows["D_true"]["deciding_pool"], rows["D_blur"]["deciding_pool"])
    bt, bb = rows["D_true"]["bks_goat"]["all"], rows["D_blur"]["bks_goat"]["all"]
    bg = fk_code(bt, bb) if _iv_ok(bt) and _iv_ok(bb) else {"code": None, "reading": "no BKS+GOAT interval"}
    pt, pb = rows_pass["D_true"]["deciding_pool"], rows_pass["D_blur"]["deciding_pool"]
    fk_pass = S.passing_code(lambda: fk_code(pt, pb), _iv_ok(pt) and _iv_ok(pb)) if refused else fk
    rep = dict(out, rows=rows, fk=fk, fk_bks_goat=bg, agree=fk["code"] == bg["code"],
               fk_passing_only=fk_pass, label=S.refusal_label(fk["code"], fk_pass["code"]),
               next="full row" if fk["code"] == "FK-shut" else fk["next"])
    P.save(report_path(args.name), rep)
    dt, db = rows["D_true"]["deciding_pool"], rows["D_blur"]["deciding_pool"]
    print(f"{args.name}: D_true {dt['mean']:+.3f} [{dt['lo90']:+.3f}, {dt['hi90']:+.3f}], D_blur {db['mean']:+.3f} "
          f"[{db['lo90']:+.3f}, {db['hi90']:+.3f}] on the pool -> {fk['code']} (BKS+GOAT {bg['code']}). "
          f"Next: {rep['next']}. Covers: {covers(args.name)['covers']}")


# --- the full row, only after FK-shut --------------------------------------------------------------------------------------

def require_shut(m, name):
    rp = report_path(name)
    rep = json.loads(rp.read_text()) if rp.exists() else None
    why = report_refusal(rep, name, ((m or {}).get(phase_answers(name)) or {}).get("sha256"))
    if why:
        raise SystemExit(why)
    return rep


def cmd_search_full(args):
    """One shard of a codec's full row (about 262 renders a part), only after its short report reads FK-shut:
    `scratch_search.search_row_part` unchanged (step 1 at 200, step 2, the final) with the hashed dry guitar and its
    start value. -> search-full/<name>/<pkey>.json."""
    m = require_codec(PHASE_DRY, phase_answers(args.name))
    build = require_build(m)
    require_name(args.name, SEARCHED, build)
    require_shut(m, args.name)
    require_control()
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import note_replay as NR

    draw = S.require_draw()
    sd = NR.Stored()
    render_guards(draw, sd)
    mine = shard_of(draw["parts"], args.shard)
    if args.first:
        mine = mine[:args.first]
    lists = C.mic_lists()
    total, t0 = 0, time.time()
    for p in mine:
        out = search_path(args.name, p["pkey"], full=True)
        if out.exists():
            continue
        disk_guard()
        x32, sha = load_dry(args.name, p["pkey"], build)
        rec = S.search_row_part(p, args.name, REF, x32, S.load_ref_blank(sd, p, REF), CB.new_renderer, lists, out,
                                f"{LEDGER_ID} {PHASE}", start_ref=start_ref_of(args.name, p["pkey"], sha),
                                dry_sha256=sha)
        total += rec.get("renders", 0)
        print(f"shard {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s", flush=True)
    print(f"FS-CODEC SEARCH FULL DONE {args.name} {args.shard[0]}/{args.shard[1]}: {total} renders in "
          f"{time.time() - t0:.0f} s")


def cmd_answers_full(args):
    """The full row's answers (zero renders): refused unless every record's first 50 step-1 values equal the short
    record's (`first_fifty_refusal`) and its dry guitar is the hashed build's; `scratch_search.answer_parts`; the
    refusal stop. -> answers-full-<name>.json; its sha256 -> phase_scratch_codec_answers_<m2l or dac>_full."""
    m = require_codec(PHASE_DRY, phase_answers(args.name))
    build = require_build(m)
    require_name(args.name, SEARCHED, build)
    require_shut(m, args.name)
    S.never_overwrite(answers_path(args.name, full=True))
    from learn import pipeline_fix as P

    draw = S.require_draw()
    full, short = {}, {}
    for p in draw["parts"]:
        k = p["pkey"]
        for d, fl in ((full, True), (short, False)):
            sp = search_path(args.name, k, full=fl)
            if not sp.exists():
                raise SystemExit(f"{k}: not searched{' (full row)' if fl else ''}")
            d[k] = json.loads(sp.read_text())
        want = build["names"][args.name][k]["sha256"]
        if "refused" not in full[k] and full[k].get("dry_sha256") != want:
            raise SystemExit(f"{k}: the full record's dry guitar is not the hashed build's")
    why = first_fifty_refusal(full, short)
    if why:
        raise SystemExit(why)
    parts, refused = S.answer_parts(draw, full, lambda k: S.file_sha(search_path(args.name, k, full=True)))
    out = {"plan": PLAN, "row": ROW + " (full)", "dry": args.name, "ref": S.REF_NAME[REF],
           "draw_sha256": S.file_sha(S.draw_path()), "build_sha256": S.file_sha(build_path()),
           "time": time.strftime("%Y-%m-%d %H:%M:%S"), "renders": sum(r.get("renders", 0) for r in full.values()),
           "refused": refused, "stopped": S.stopped(refused), "parts": parts}
    P.save(answers_path(args.name, full=True), out)
    print(f"FS-CODEC ANSWERS FULL {args.name}: {len(parts)} parts, {len(refused)} refused; sha256 "
          f"{S.file_sha(answers_path(args.name, full=True))} (into the ledger as {phase_answers(args.name, True)})")


def cmd_score_full(args):
    """One shard of the full row's score (about 20 renders a part): `scratch_search.score_row_part` unchanged."""
    score_shard(args, True)


def cmd_read_full(args):
    """The full row's reading (zero renders), once: `scratch_search.read_row_parts` on this row and on rows (b) and
    (c); per arm (G, G_shrunk) D_true and D_blur against rows (b) and (c)'s same arm, `fk_code` per arm on the pool,
    then `park_code`. -> rows-full-<name>.json, report-full-<name>.json."""
    m = require_codec(PHASE_DRY, phase_answers(args.name), phase_answers(args.name, True))
    require_build(m)
    require_name(args.name, SEARCHED)
    require_shut(m, args.name)
    ans = require_answers(m, args.name, True)
    never_overwrite_all([rows_path(args.name, True), report_path(args.name, True)])
    from learn import note_replay as NR
    from learn import pipeline_fix as P

    draw = S.require_draw()
    sd = NR.Stored()
    rby = {p["pkey"]: p for p in NR.require_draw()["parts"]}
    sha = S.file_sha(answers_path(args.name, True))
    per, refused, replaced, miss = S.read_row_parts(draw, ans, sha, lambda k: score_path(args.name, k, True), sd, rby)
    out = dict(S.report_body(ROW + " (full)", args.name, sha, per, refused, replaced, miss), covers=covers(args.name))
    if out["stopped"]:
        P.save(report_path(args.name, True), dict(out, rows=None, park=None))
        print(f"{args.name} (full): STOPPED ({out['stop_reason']})")
        return
    comp = {}
    for row in (STEM_ROW, BOTH_ROW):
        a = S.require_hash(S.phase_answers(row), S.answers_path(row))
        comp[row] = S.read_row_parts(draw, a, S.file_sha(S.answers_path(row)), lambda k, r=row: S.score_path(r, k),
                                     sd, rby)[0]
    arms, codes = {}, {}
    for arm in ("G", "G_shrunk"):
        d_true, d_blur = SN.paired_values(per, comp[STEM_ROW], arm), SN.paired_values(per, comp[BOTH_ROW], arm)
        arms[arm] = {"G": SN.set_rows(sd, draw, {k: v[arm] for k, v in per.items() if v and v.get(arm) is not None}),
                     "D_true": SN.set_rows(sd, draw, d_true), "D_blur": SN.set_rows(sd, draw, d_blur)}
    P.save(rows_path(args.name, True), dict(out, rows=arms))     # the rows are saved before the codes are read
    why = deciding_refusal({f"{arm} {q}": arms[arm][q] for arm in arms for q in arms[arm]})
    if why:
        P.save(report_path(args.name, True), dict(out, rows=arms, park=None, stopped=True, stop_reason=why))
        print(f"{args.name} (full): STOPPED ({why}); to the user")
        return
    fks = {arm: fk_code(arms[arm]["D_true"]["deciding_pool"], arms[arm]["D_blur"]["deciding_pool"]) for arm in arms}
    for arm in arms:
        codes[arm] = fks[arm]["code"]
    park = park_code(codes)
    P.save(report_path(args.name, True), dict(out, rows=arms, fk=fks, park=park))
    print(f"{args.name} (full): " + "; ".join(f"{a} {c}" for a, c in codes.items()) + f" -> {park['reading']}")


# --- main ------------------------------------------------------------------------------------------------------------------

COMMANDS = {"prep": cmd_prep, "build": cmd_build, "start": cmd_start, "control": cmd_control, "search": cmd_search,
            "answers": cmd_answers, "score": cmd_score, "read": cmd_read, "search-full": cmd_search_full,
            "answers-full": cmd_answers_full, "score-full": cmd_score_full, "read-full": cmd_read_full}
NEEDS_NAME = ("start", "search", "answers", "score", "read", "search-full", "answers-full", "score-full", "read-full")


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
    ap.add_argument("--first", type=int, default=0, help="search only this shard's first n parts (the re-timing)")
    args = ap.parse_args(argv)
    if args.cmd in NEEDS_NAME and not args.name:
        ap.error(f"{args.cmd} needs --name")
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
