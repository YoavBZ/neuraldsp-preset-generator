"""The rebuild's re-derivation, the rows (`docs/rederive-plan.md` section 7; Unit 4; ledger `preset-ladder`
`phase_scratch_rederive`, then `_answers_<row>`, `_bench_outcome`, `_outcome`): the checks, the floors, the null
build, every row's search, answers and score, and the two reads.

| Row | Dry guitar of the search | When |
|---|---|---|
| `xf-now` | today's rule handed `in-M` (the ladder's) | first (stage 1) |
| `xf-fix` | the frozen rule handed `in-M` (Unit 3's `build-bench`) | only if stage 1 goes on (stage 2) |
| `xf-tuning`, `xf-mutes`, `xf-tilt`, `xf-levels` | the chain cells in `in-M` (the ladder's) | only if the code asks |
| `xf-null` | X with a negligible change (`null-build`) | only if the code asks |
| `fs-refit` | `rf2`: build 2's notes, the frozen rule, the true DI (Unit 3's `build-real`) | the bridge |

    $MAIN -m learn.rederive_rows check-score --for bench    # row (c) re-scored as the bench scores (score_exact_part)
    $MAIN -m learn.rederive_rows check-search --for bench   # row (c)'s first 10 evaluations as the bench searches
    $MAIN -m learn.rederive_rows search --row xf-now --shard 0/3 [--rerun]
    $MAIN -m learn.rederive_rows answers --row xf-now       # zero renders -> phase_scratch_rederive_answers_now
    $MAIN -m learn.rederive_rows score --row xf-now --shard 0/3 [--rerun]
    $MAIN -m learn.rederive_rows read --stage 1             # zero renders, once: D_now, xf_stage1's code
    $MAIN -m learn.rederive_rows floors --shard 0/3         # beside: the target through xf-fix and the 4 chain cells
    $MAIN -m learn.rederive_rows search --row xf-fix ...    # only after stage 1 went on; then answers, score
    $MAIN -m learn.rederive_rows read --stage 2             # zero renders, once: D_fix, the gain, xf_read's code
    $MAIN -m learn.rederive_rows null-build                 # zero renders, only if the code asks
    $MAIN -m learn.rederive_rows read --stage rungs         # zero renders: the rung and null rows, beside
    $MAIN -m learn.rederive_rows check-score --for real     # row (c) re-scored as the bridge scores (score_row_part)
    $MAIN -m learn.rederive_rows check-search --for real
    $MAIN -m learn.rederive_rows floor-real --shard 0/3     # beside only: row (b)'s answer through rf2
    $MAIN -m learn.rederive_rows search --row fs-refit --carry   # once, one process: build 2's records, all or none
    $MAIN -m learn.rederive_rows search --row fs-refit ...  # then answers (-> _answers_refit), score
    $MAIN -m learn.rederive_rows read-real                  # zero renders, once: D_real, rf_code
    $MAIN -m learn.rederive_rows reproduce                  # zero renders: D_list and build 2 less row (b), stored

Bench rows use `scratch_exact`'s pattern: `scratch_search.search_row_part` unchanged, the exact-notes test's records
(blanked outside the search half), its start reference (`scratch_exact.start_reference`) and score
(`scratch_exact.score_exact_part`), lag 0 (`synthetic_part`), `xn_answer_parts`. The real row uses `scratch_notes`'
shared steps unchanged with its own keys and folders: `scratch_notes.start_reference`, `search_row_part` on `xlnoG@-3`,
`answer_parts`, `score_row_part`, `read_row_parts`. A guitar byte-identical to a searched one takes that record byte for
byte (`CARRY_FROM`; on the real row build 2's, after its start reference repeats). The search opens nothing scored:
every file it reads goes through `search_open` (`scratch_exact`'s forbidden files and this module's own).

Reads: intervals from `scratch_notes.set_rows` on BKS+GOAT, all 47 beside; labels only from `paired_reading` and
`number_reading`; S1 (a technical refusal reruns once, then reads at Cen; the passing-only read beside,
`refusal-sensitive` when the codes differ); the declared splits (`SPLITS`). Before a read, `reproduce` must give D_list
and build 2 less row (b) from the stored files exactly as the exact-notes read stored them.

Every command refuses unless this checkout runs main's code (this module and `scratch_rederive`'s pinned files) and
keys, and main holds the hashes the command reads (each command's keys). Shards: at most 3.

The other units' files, read through their own code: Unit 3's builders (`learn/rederive_fit.py`, imported, never
copied): `build_record_path("bench" | "real")` (fit/build-bench.json, fit/build-real.json; per part
`{file_sha256, audio_sha256, ...}`) and `guitar_path(row, pk)` (dry/xf-fix/, dry/fs-refit/), hashed on main through
`phase_scratch_rederive_frozen` as `freeze` prints it (`sha256`: frozen.json's; `build_bench.sha256`,
`build_real.sha256`; `rule`, `stop`). The ladder: `phase_scratch_rederive_ladder` `sha256`. The bench outcome:
`phase_scratch_rederive_bench_outcome` `code` (`bridge_user_go` true when the user runs the bridge on another code).
Each row's answers: `answers_path(row)` (public; Unit 2 reads it), hashed as `phase_scratch_rederive_answers_<row>`
`sha256`. The null row's change (`NULL_CHANGE`): X scaled by 0.01 dB, `at_lufs`' own tolerance.

The pure parts (the carry, the gates, the shard rule, the splits' keys, the design-time and tilt parts, the codes with
S1, the forbidden paths, `null_change_refusal`) are tested in tests/test_rederive_rows.py on synthetic keys; the
commands behind fakes.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import time

from learn import note_transcribe as NT
from learn import rederive_fit as RF
from learn import scratch_exact as SE
from learn import scratch_notes as SN
from learn import scratch_rederive as RD
from learn import scratch_search as S

LEDGER_ID = RD.LEDGER_ID                 # preset-ladder
PLAN = "docs/rederive-plan.md section 7"
MODULE = "learn/rederive_rows.py"
OWN_FILES = (MODULE,) + tuple(RF.OWN_FILES)   # this module and Unit 3's, whose paths and formats it reads
CODE_FILES = OWN_FILES + RD.CODE_FILES   # then the core's pinned files
NOW_ROW, FIX_ROW, NULL_ROW, REAL_ROW = RD.NOW_ROW, RD.FIX_ROW, RD.NULL_ROW, RD.REAL_ROW
RUNG_ROWS = RD.RUNG_ROWS
BENCH_ROWS = RD.BENCH_ROWS
ROWS = RD.ROWS
BASE = "xn-bank"                         # D = G(row) - G(xn-bank), paired per part
LIST_ROW = "xn-list"                     # D_list = G(xn-list) - G(xn-bank): reproduced; D_list - D_now beside
REAL_DRY = RD.REAL_BUILD                 # "rf2": the bridge's dry guitar
REAL_REF = SN.REF                        # "xlnoG": the bridge searches against xlnoG@-3, as fs-notes
REAL_FROM = SE.BUILD2                    # "b2": the real row's comparator and carry source
STEM_ROW, BOTH_ROW = SE.STEM_ROW, SN.COMPARATOR   # rows (b) and (c)
MAX_SHARDS = 3
FLOOR_ROWS = (FIX_ROW,) + RUNG_ROWS      # floors beside: the target through xf-fix and the four chain cells
FLOOR_REPEAT = LIST_ROW                  # the stored xn-list floor repeats on the checks' two parts
GO_ON = "go-on"                          # stage 1's "goes on" in a code comparison (it has no code of its own)

# A guitar byte-identical to a row searched before it takes that row's record byte for byte, the first that matches
CARRY_FROM = {NOW_ROW: (BASE, LIST_ROW), FIX_ROW: (BASE, LIST_ROW, NOW_ROW),
              **{r: (BASE, LIST_ROW, NOW_ROW, FIX_ROW) for r in RUNG_ROWS}, NULL_ROW: (BASE,)}

# The gates on main's bench outcome (plan section 8's "Next" column)
RUNG_CODES = ("XF-worse", "XF-part", "XF-undecided")   # "rung rows" in their Next
NULL_CODES = ("XF-part",)                # "the null row if the guitars are near X"
BRIDGE_CODES = ("XF-closed", "XF-part")  # "the bridge runs"; on any other code the bridge is the user's call
BRIDGE_GO = "bridge_user_go"
OUTCOME_CODE = "code"

# The hashes on main (the field names the hash PRs write)
LADDER_FIELD = "sha256"                  # phase_scratch_rederive_ladder: ladder.json's sha256 (NT.require_file_hash)
BUILDS = RF.BUILDS                       # Unit 3's: {"bench": "xf-fix", "real": "fs-refit"}
FROZEN_FIELDS = {"bench": "build_bench", "real": "build_real"}   # in `rederive_fit.freeze_body`

# The null row's change: X scaled by 0.01 dB (None would refuse `null-build`)
NULL_CHANGE = {"kind": "gain_db", "value": 0.01}   # at_lufs' own tolerance (the orchestrator's call, 2026-11-25)
NULL_KINDS = ("gain_db",)

ARMS = {"answer": "G", "shrunk": "G_shrunk", "cp50": "G_cp50", "cp100": "G_cp100", "cp200": "G_cp200"}
DECIDING_ARM = "answer"
SPLITS = ("the_40", "clean", "crunch", "all_47", "panel", "shrunk", "cp50", "cp100", "cp200", "cluster_left_out",
          "one_per_partner", "without_design_time", "tilt_15_vs_25")
SEEN_LABEL = "seen before the declaration (the 15 tilt parts against the 25)"
SEEN = {"D_list": (0.321, 0.180, 0.462), "b2_less_row_b": (0.274, 0.186, 0.361),
        "D_list_without_design_time": (0.247, 0.153, 0.342), "D_list_one_per_partner": (0.261, 0.149, 0.372)}

FORBIDDEN_PREFIXES = ("answers-", "rows-", "report-", "read-", "floors-real-")
FORBIDDEN_NAMES = ("answers.json", "rows.json", "report.json", "reproduce.json")
FORBIDDEN_DIRS = ("score", "score-rerun", "floors", "floors-real")


# --- the gates (pure) -------------------------------------------------------------------------------------------------

def shard_refusal(shard):
    """(Pure.) Why a shard may not run, or None: k/n with 0 <= k < n <= MAX_SHARDS."""
    k, n = shard
    if not (0 <= k < n <= MAX_SHARDS):
        return f"shard {k}/{n}: at most {MAX_SHARDS} render processes"
    return None


def bench_code(m):
    """(Pure.) main's bench outcome code, or None."""
    rec = (m or {}).get(RD.PHASE_BENCH_OUTCOME)
    return rec.get(OUTCOME_CODE) if isinstance(rec, dict) else None


def row_refusal(row, m, stage1=None):
    """(Pure.) Why a row may not run, or None. `xf-fix`: stage 1 went on (`stage1`: the stage-1 go record) from
    main's `xf-now` answers. The rung rows and the null row: main's bench code asks for them. `fs-refit`: the bench code
    is XF-closed or XF-part, or the user's go is recorded (`bridge_user_go`)."""
    if row not in ROWS:
        return f"unknown row {row!r}"
    if row == FIX_ROW:
        if not stage1:
            return "xf-fix runs only after stage 1's read (`read --stage 1`)"
        if not stage1.get("go_on"):
            return (f"stage 1 read {stage1.get('code')}{' (' + stage1['label'] + ')' if stage1.get('label') else ''}: "
                    "xf-fix does not run; to the user")
        want = ((m or {}).get(RD.answers_key(NOW_ROW)) or {}).get("sha256")
        if not want or stage1.get("answers_now_sha256") != want:
            return "stage 1's read is not from main's xf-now answers"
    if row in RUNG_ROWS and bench_code(m) not in RUNG_CODES:
        return f"the bench code {bench_code(m)} does not ask for the rung rows ({list(RUNG_CODES)})"
    if row == NULL_ROW and bench_code(m) not in NULL_CODES:
        return f"the bench code {bench_code(m)} does not ask for the null row ({list(NULL_CODES)})"
    if row == REAL_ROW:
        rec = (m or {}).get(RD.PHASE_BENCH_OUTCOME)
        if not isinstance(rec, dict):
            return f"main has no {RD.PHASE_BENCH_OUTCOME}: the bridge waits for the bench's code"
        if rec.get(OUTCOME_CODE) not in BRIDGE_CODES and rec.get(BRIDGE_GO) is not True:
            return (f"the bench code {rec.get(OUTCOME_CODE)} does not run the bridge: it is the user's call "
                    f"({BRIDGE_GO} in {RD.PHASE_BENCH_OUTCOME})")
    return None


def floor_repeat_refusal(flags):
    """(Pure.) Why xf-fix may not search, or None: the stored xn-list floor must have repeated on each check part.
    flags: {pkey: xn_list_repeats or None (floors not run there)}."""
    missing = sorted(k for k, v in flags.items() if v is None)
    if not flags or missing:
        return f"the floors have not run on the check parts ({len(missing) or 'none'}): `floors` first (phase 3c)"
    bad = sorted(k for k, v in flags.items() if v is not True)
    if bad:
        return f"the stored xn-list floor did not repeat on {len(bad)} check part(s): a determinism break, to the user"
    return None


def carry_all_or_none(cands, mine, theirs):
    """(Pure.) `scratch_notes.cmd_carry`'s rule: every candidate's recomputed start reference must have build 2's render
    sha256, else none is carried. mine, theirs: {pkey: render_sha256 or None}. -> (carried, mismatches)."""
    mism = SN.carry_mismatches({k: mine.get(k) for k in cands}, theirs)
    return ([] if mism else sorted(cands)), mism


def carry_source(row, sha, source_shas):
    """(Pure.) The row searched before `row` whose guitar is byte-identical to this one (`CARRY_FROM`'s order, the
    first that matches), or None. source_shas: {row: that row's guitar sha256 for the part, or None}."""
    for r in CARRY_FROM.get(row, ()):
        if sha and source_shas.get(r) == sha:
            return r
    return None


def null_change_refusal(change):
    """(Pure.) Why the null row's change may not be used, or None: a declared {kind, value} with a known kind and a
    finite, non-zero value."""
    if change is None:
        return "the null row's change is not declared (NULL_CHANGE): to the coordinator before null-build"
    if not isinstance(change, dict) or change.get("kind") not in NULL_KINDS:
        return f"the null row's change must be one of {list(NULL_KINDS)}"
    v = change.get("value")
    if not isinstance(v, (int, float)) or not math.isfinite(v) or v == 0:
        return "the null row's change needs a finite, non-zero value"
    return None


# --- the read's parts and codes (pure) --------------------------------------------------------------------------------

def design_time_parts(list_refused, tilt_x, tilt_list, deciding_keys):
    """(Pure.) The two design-time parts, by rule from hashed files (no part key in git): every part refused in the
    exact-notes test's `xn-list` answers (the refused sw50r part), and the deciding part whose `xn-list` tilt lies
    furthest from X's (GOAT item_69, +10.1 -> -7.1 dB/s). tilt_*: {pkey: dB/s or None (no tilt)}.
    The rule checks its own answer: exactly one refused part and exactly one part at the top tilt gap (above zero, no
    tie), two parts in all; anything else refuses (the declared split names two parts)."""
    refused = sorted(set(list_refused))
    gaps = {k: abs((tilt_x.get(k) or 0.0) - (tilt_list.get(k) or 0.0)) for k in deciding_keys}
    top = max(gaps.values()) if gaps else 0.0
    at_top = sorted(k for k, g in gaps.items() if g == top and g > 0)
    if len(refused) != 1:
        raise SystemExit(f"the design-time rule finds {len(refused)} refused xn-list part(s), not 1: to the user")
    if len(at_top) != 1:
        raise SystemExit(f"the design-time rule finds {len(at_top)} part(s) at the top tilt gap, not 1: to the user")
    if refused == at_top:
        raise SystemExit("the design-time rule's two parts are one part: to the user")
    return sorted(refused + at_top)


def tilt_parts(tilt_applied, deciding_keys):
    """(Pure.) The tilt parts of the 40: those whose `xn-list` rebuild applied a sustain tilt (15 of the 40, seen)."""
    return sorted(k for k in deciding_keys if tilt_applied.get(k))


def contributions(vals, keys):
    """(Pure.) `vals` with every part outside `keys` set to 0.0: the keys' contribution to the mean of the 40."""
    return {k: (v if k in keys else 0.0) for k, v in vals.items()}


def eff_code(rec):
    """(Pure.) A read's code for S1's comparison: its code, or "go-on" for stage 1's going on, or None."""
    if not isinstance(rec, dict):
        return None
    return rec.get("code") or (GO_ON if rec.get("go_on") else None)


def with_passing(read_fn, itt, passing):
    """(Pure.) S1: the deciding code from the intent-to-treat intervals (`itt`, a tuple for `read_fn`); beside, the
    passing-only code (None when nothing was refused; "no passing-only interval" when any is missing) and
    `refusal-sensitive` when the two codes differ. -> (code, passing code or None, label or None)."""
    code = read_fn(*itt)
    if passing is None:
        return code, None, None
    ok = all(RD.iv_ok(x) for x in passing)
    cp = S.passing_code(lambda: read_fn(*passing), ok)
    label = S.refusal_label(eff_code(code), eff_code(cp)) if ok else None
    return code, cp, label


def is_forbidden(path):
    """(Pure.) Whether a search may not open `path`: `scratch_exact`'s forbidden files and folders, and this module's
    answers, reads, reports, floors and scores."""
    path = pathlib.PurePath(path)
    if SE.is_forbidden(path):
        return True
    name = path.name
    return (name in FORBIDDEN_NAMES or name.startswith(FORBIDDEN_PREFIXES)
            or any(part in FORBIDDEN_DIRS for part in path.parent.parts[-3:]))


def search_open(path):
    """Every file a search reads goes through here: a forbidden one refuses."""
    if is_forbidden(path):
        raise SystemExit(f"{pathlib.PurePath(path).name}: the search never opens it")
    return pathlib.Path(path)


# --- paths ------------------------------------------------------------------------------------------------------------

def rows_dir():
    return RD.rederive_dir()


def guitar_path(row, pk):
    """A stored dry guitar: the ladder's rows and xf-null under PF/fs/rederive/dry/<row>/ (this module's and the
    core's), xf-fix and fs-refit's rf2 where Unit 3's builders wrote them (`rederive_fit.guitar_path`)."""
    if row in BUILDS.values():
        return RF.guitar_path(row, pk)
    if row not in RD.LADDER_WRITES + (NULL_ROW,):
        raise ValueError(row)
    return rows_dir() / "dry" / row / f"{SE._f(pk)}.npy"


def build_path(kind):
    """Unit 3's build record (`rederive_fit.build_record_path`): fit/build-bench.json or fit/build-real.json."""
    return RF.build_record_path(kind)


def null_build_path():
    return rows_dir() / "build-null.json"


def stage1_path():
    """Stage 1's go record: the code, go_on and the answers' sha256 only (the one file xf-fix's search reads)."""
    return rows_dir() / "stage1-go.json"


def check_dir(side, kind):
    if side not in ("bench", "real") or kind not in ("check-score", "check-search"):
        raise ValueError((side, kind))
    return rows_dir() / "checks" / side / kind


def search_path(row, pk):
    return rows_dir() / "search" / row / f"{SE._f(pk)}.json"


def start_path(row, pk):
    return rows_dir() / "start-ref" / row / f"{SE._f(pk)}.json"


def answers_path(row):
    """A row's answers file (any of `ROWS`: the bench rows and `fs-refit`), PF/fs/rederive/answers-<row>.json; its
    sha256 is main's `phase_scratch_rederive_answers_<row>` before the score. Public: `rederive_diag` reads it."""
    if row not in ROWS:
        raise ValueError(f"unknown row {row!r}: one of {list(ROWS)}")
    return rows_dir() / f"answers-{row}.json"


def score_path(row, pk):
    return rows_dir() / "score" / row / f"{SE._f(pk)}.json"


def floor_path(kind, pk):
    if kind not in ("floors", "floors-real"):
        raise ValueError(kind)
    return rows_dir() / kind / f"{SE._f(pk)}.json"


def read_path(kind, name):
    if kind not in ("rows", "report"):
        raise ValueError(kind)
    return rows_dir() / f"{kind}-{name}.json"


def repeat_path(pk):
    """The xn-list floor's repeat flag on a check part (no distance): xf-fix's search reads it."""
    return rows_dir() / "floor-repeat" / f"{SE._f(pk)}.json"


def carry_path():
    """The bridge's carry record (`search --row fs-refit --carry`), written once."""
    return rows_dir() / "carry-real.json"


def reproduce_path():
    return rows_dir() / "reproduce.json"


# --- the guards -------------------------------------------------------------------------------------------------------

def pinned_identity():
    """This module and Unit 3's `rederive_fit` equal to origin/main's (git diff --quiet); the core checks its own
    pinned files. -> {file: same}."""
    return {f: SE._git("diff", "--quiet", "origin/main", "--", f).returncode == 0 for f in OWN_FILES}


def require_rows(*phases):
    """Refuse unless this checkout runs main's code and keys (`scratch_rederive.require_rederive`, this module, the
    redo's guard) and main holds `phases`. -> main's `preset-ladder` entry."""
    m = RD.require_rederive(*phases)
    bad = [f for f, ok in pinned_identity().items() if not ok]
    if bad:
        raise SystemExit(f"this checkout's {bad} differ from main's: run from merged code")
    _, why = NT.redo_on_main()
    if why:
        raise SystemExit(why)
    return m


def bench_phases(row):
    """(Pure.) The keys a bench row's search, answers and score read on main."""
    ph = [RD.PHASE_LADDER]
    if row in (FIX_ROW,) + RUNG_ROWS:
        ph.append(RD.PHASE_FROZEN)
    if row == FIX_ROW:
        ph.append(RD.answers_key(NOW_ROW))
    if row in RUNG_ROWS + (NULL_ROW,):
        ph.append(RD.PHASE_BENCH_OUTCOME)
    return tuple(ph)


REAL_PHASES = (RD.PHASE_FROZEN, RD.PHASE_BENCH_OUTCOME, SE.PHASE_B2_ANSWERS)


def row_phases(row):
    return REAL_PHASES if row == REAL_ROW else bench_phases(row)


def stage1_record():
    p = search_open(stage1_path())                     # allowed: xf-fix's search reads go_on here
    return json.loads(p.read_text()) if p.exists() else None


def ladder_record(m):
    """ladder.json, refused unless its sha256 is main's phase_scratch_rederive_ladder `sha256` and its proofs held."""
    p = search_open(RD.ladder_path())
    if not p.exists():
        raise SystemExit("no ladder.json (run `scratch_rederive ladder` first)")
    why = SE.field_refusal(m, RD.PHASE_LADDER, LADDER_FIELD, S.file_sha(p))
    if why:
        raise SystemExit(why)
    rec = json.loads(p.read_text())
    if not rec.get("proofs_hold"):
        raise SystemExit("ladder.json's proofs did not hold")
    return rec


def frozen_refusal(entry, kind, sha):
    """(Pure.) Why Unit 3's build record may not be used, or None: main's phase_scratch_rederive_frozen body (as
    `rederive_fit.freeze` prints it) must hold its sha256 under `build_bench` or `build_real`, for that build's row."""
    rec = (entry or {}).get(RD.PHASE_FROZEN)
    field = FROZEN_FIELDS[kind]
    body = rec.get(field) if isinstance(rec, dict) else None
    if not isinstance(body, dict) or not body.get("sha256"):
        return f"main's {RD.PHASE_FROZEN} has no {field} sha256: `rederive_fit freeze` and its hash PR first"
    if body["sha256"] != sha:
        return f"build-{kind}.json's sha256 {sha[:12]} is not main's {RD.PHASE_FROZEN} {field} {body['sha256'][:12]}"
    if body.get("row") != BUILDS[kind]:
        return f"main's {RD.PHASE_FROZEN} {field} is for {body.get('row')}, not {BUILDS[kind]}"
    return None


def build_refusal(rec, kind, frozen):
    """(Pure.) Why a hashed build record may not drive a row, or None: it is the build of its row, made with main's
    frozen rule and stop, every part names its guitar (`file_sha256`, `audio_sha256`), and for the real build the rule
    off was X on every part."""
    row = BUILDS[kind]
    if rec.get("row") != row:
        return f"build-{kind}.json is for {rec.get('row')}, not {row}"
    rule = ((frozen or {}).get("rule") or {}).get("candidate")
    if rec.get("rule") != rule or rec.get("stop") != (frozen or {}).get("stop"):
        return f"build-{kind}.json was not made with main's frozen rule and stop"
    parts = rec.get("parts") or {}
    bad = sorted(k for k, r in parts.items() if not (r.get("file_sha256") and r.get("audio_sha256")))
    if not parts or bad:
        return f"build-{kind}.json names no {row} guitar for {len(bad) or 'any'} part(s)"
    if kind == "real":
        off = rec.get("rule_off_is_x") or {}
        if not off.get("of") or off.get("held") != off.get("of") or off["of"] != len(parts):
            return "build-real.json: the rule off was not X on every part"
    return None


def fit_build(m, kind):
    """Unit 3's build record (`rederive_fit.build_record_path`), refused unless main's phase_scratch_rederive_frozen
    holds frozen.json's sha256 and this record's (`frozen_refusal`) and the record is that build's (`build_refusal`)."""
    fp = search_open(RF.frozen_path())
    if not fp.exists():
        raise SystemExit("no frozen.json (`rederive_fit freeze` first)")
    NT.require_file_hash(m, RD.PHASE_FROZEN, fp)
    p = search_open(build_path(kind))
    if not p.exists():
        raise SystemExit(f"no build-{kind}.json (`rederive_fit build-{kind}` first)")
    why = frozen_refusal(m, kind, S.file_sha(p))
    if why:
        raise SystemExit(why)
    rec = json.loads(p.read_text())
    why = build_refusal(rec, kind, m.get(RD.PHASE_FROZEN))
    if why:
        raise SystemExit(why)
    return rec


def null_record():
    p = search_open(null_build_path())
    if not p.exists():
        raise SystemExit("no build-null.json (run `null-build` first)")
    return json.loads(p.read_text())


def source_of(row):
    """(Pure.) Which record declares a row's guitar."""
    if row == BASE:
        return "b2"
    if row == LIST_ROW:
        return "xb"
    return {FIX_ROW: "bench", NULL_ROW: "null", REAL_DRY: "real", REAL_ROW: "real"}.get(row, "ladder")


def file_entry(row, pk, w):
    """(Pure.) A stored guitar's {file_sha256, audio_sha256}: the ladder's and the null build's under `files[<row>]`,
    Unit 3's builds' flat per part (`rederive_fit`'s format), or None."""
    rec = w.get(source_of(row))
    if rec is None:
        return None
    part = (rec.get("parts") or {}).get(pk) or {}
    if source_of(row) in ("bench", "real"):
        return part or None
    return (part.get("files") or {}).get(row)


def guitar_row(row):
    """(Pure.) The folder a row's stored guitar sits in: fs-refit's rf2 under Unit 3's `fs-refit`, the others their
    own."""
    return BUILDS["real"] if row in (REAL_ROW, REAL_DRY) else row


def guitar_sha(row, pk, w):
    """The declared sha256 (of the float32 .npy bytes) of a row's dry guitar for a part, or None when its record is not
    loaded. w: the loaded records (`b2` build 2, `xb` the exact build, `ladder`, `bench`, `null`, `real`)."""
    src = source_of(row)
    rec = w.get(src)
    if rec is None:
        return None
    if src == "b2":
        return rec["parts"][pk]["arms"][SE.BANK_ARM]["sha256"]
    if src == "xb":
        return rec["parts"][pk]["guitars"][LIST_ROW]["sha256"]
    return (file_entry(row, pk, w) or {}).get("audio_sha256")


def load_guitar(row, pk, w):
    """A row's dry guitar for a part, float32, refused unless its file and its samples are the declared ones."""
    import numpy as np

    want = guitar_sha(row, pk, w)
    if row == BASE:
        x32 = NT.load_dry(SE.BANK_ARM, pk, w["b2"])
    elif row == LIST_ROW:
        x32 = np.load(search_open(SE.dry_path(LIST_ROW, pk))).astype(np.float32)
    else:
        g = guitar_row(row)
        path = search_open(guitar_path(g, pk))
        if S.file_sha(path) != (file_entry(row, pk, w) or {}).get("file_sha256"):
            raise SystemExit(f"{pk}: {g}'s file is not the declared one")
        x32 = np.load(path).astype(np.float32)
    if not want or S.npy_sha(x32) != want:
        raise SystemExit(f"{pk}: {row}'s dry guitar is not the declared one")
    return x32


def null_guitar(x32, change):
    """X with the declared negligible change (`NULL_CHANGE`), float32: "gain_db" scales X by that gain."""
    why = null_change_refusal(change)
    if why:
        raise SystemExit(why)
    import numpy as np

    return (np.asarray(x32, np.float64) * 10 ** (change["value"] / 20)).astype(np.float32)


def bench_world(m, row, b2, xb):
    """The records a bench row's guitars are declared in: build 2, the exact build, the ladder; Unit 3's bench build
    for xf-fix and the rung rows (which carry from it); the null build for the null row (each guitar recomputed from X
    and checked)."""
    w = {"b2": b2, "xb": xb, "ladder": ladder_record(m)}
    if row in (FIX_ROW,) + RUNG_ROWS:
        w["bench"] = fit_build(m, "bench")
    if row == NULL_ROW:
        w["null"] = null_record()
        if w["null"].get("change") != NULL_CHANGE or null_change_refusal(NULL_CHANGE):
            raise SystemExit("build-null.json was made with another change than NULL_CHANGE")
    return w


def require_bench_checks(side="bench"):
    """Both checks of `side` ran and passed (`scratch_notes.checks_passed`). -> {kind: result}."""
    res = {}
    for kind in ("check-score", "check-search"):
        p = check_dir(side, kind) / "result.json"
        res[kind] = json.loads(p.read_text()) if p.exists() else None
    why = SN.checks_passed(res["check-score"], res["check-search"])
    if why:
        raise SystemExit(f"{side} {why}")
    return res


def _guard_shard(args):
    why = shard_refusal(getattr(args, "shard", (0, 1)))
    if why:
        raise SystemExit(why)


# --- the checks (renders, once a side) --------------------------------------------------------------------------------

def cmd_check_score(args):
    """Row (c)'s first BKS and first GOAT part re-scored, written once a side: `--for bench` through
    `scratch_exact.score_exact_part` with the true DI, the clean record, the part's lag and C3r's stored Cen (as the
    bench scores; `scratch_exact.score_check_verdict` on the six shared settings); `--for real` through
    `scratch_search.score_row_part` (as the bridge scores; `scratch_notes.score_check_verdict`). Every held value and
    render sha256 must equal row (c)'s stored score file. -> checks/<side>/check-score/."""
    side = getattr(args, "side", "bench") or "bench"
    require_rows()
    d = check_dir(side, "check-score")
    NT.never_overwrite(d / "result.json")
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import pipeline_fix as P

    R.no_separation_beside()
    draw, sd = SE.context()
    ans = SN.comparator_answers()
    by = {p["pkey"]: p for p in draw["parts"]}
    LO._wait_cap()
    new, stored, total = {}, {}, 0
    for k in SN.check_parts(draw["parts"]):
        out = d / f"{SE._f(k)}.json"
        NT.never_overwrite(out)
        p = by[k]
        if side == "bench":
            prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
            clean = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
            rec, used = SE.score_exact_part(p, ans["parts"][k], R.di_section(prt), clean, p["lag"],
                                            sd.cen_judge((p["set"], p["unit"], p["amp"]))[p["held"]], CB.new_renderer)
        else:
            rec, used = S.score_row_part(p, ans["parts"][k], ans["parts"], BOTH_ROW,
                                         S.file_sha(S.answers_path(BOTH_ROW)), sd, CB.new_renderer)
        total += used
        P.save(out, rec)
        new[k], stored[k] = rec, json.loads(S.score_path(BOTH_ROW, k).read_text())
    verdict = SE.score_check_verdict(new, stored) if side == "bench" else SN.score_check_verdict(new, stored)
    res = {"plan": PLAN, "ledger": f"{LEDGER_ID} {RD.PHASE}", "side": side, "renders": total, **verdict,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(d / "result.json", res)
    print(f"RD CHECK-SCORE {side} {'PASS' if res['passed'] else 'FAIL'}: {total} renders; mismatches "
          f"{res['mismatches']}")


def cmd_check_search(args):
    """On the same two parts, written once a side: `scratch_search.run_part` with row (c)'s inputs (avg+mild,
    `xlnoG@-3` blanked, the part's lag) and a step-1 budget of CHECK_BUDGET, stopped after step 1; `--for bench` with
    `scratch_exact.start_reference` (the bench's start reference), `--for real` with row (c)'s start reference passed
    explicitly (as fs-notes checked it). The evaluations must equal the start of row (c)'s stored curve exactly.
    -> checks/<side>/check-search/."""
    side = getattr(args, "side", "bench") or "bench"
    require_rows()
    d = check_dir(side, "check-search")
    NT.never_overwrite(d / "result.json")
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import pipeline_fix as P

    R.no_separation_beside()
    draw, sd = SE.context()
    blur = json.loads((R.replay_dir() / "blur.json").read_text())
    if blur["draw_sha256"] != draw["replay_draw_sha256"]:
        raise SystemExit("blur.json was made from another replay draw")
    by, rby = {p["pkey"]: p for p in draw["parts"]}, {p["pkey"]: p for p in R.require_draw()["parts"]}
    lists = C.mic_lists()
    LO._wait_cap()
    new, stored, total = {}, {}, 0
    for k in SN.check_parts(draw["parts"]):
        out = d / f"{SE._f(k)}.json"
        NT.never_overwrite(out)
        p = by[k]
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        x32 = R.load_dry("avg+mild", rby[k], R.di_section(prt), blur)
        sha = blur["parts"][k]["sha256"]["avg+mild"]
        ref_blank = S.load_ref_blank(sd, p, REAL_REF)
        used = 0
        if side == "bench":
            sref, used = SE.start_reference("avg+mild", p, x32, ref_blank, CB.new_renderer,
                                            d / "start-ref" / f"{SE._f(k)}.json", sha)
        else:
            sref = p["start_ref"]["avg+mild"][REAL_REF]
        rec = S.run_part(p, "avg+mild", REAL_REF, x32, ref_blank, CB.new_renderer, lists, budget=SN.CHECK_BUDGET,
                         start_ref=sref, dry_sha256=sha, step1_only=True)
        total += rec.get("renders", 0) + used
        P.save(out, rec)
        new[k], stored[k] = rec, json.loads(S.search_path(BOTH_ROW, k).read_text())
    res = {"plan": PLAN, "ledger": f"{LEDGER_ID} {RD.PHASE}", "side": side, "renders": total,
           "budget": SN.CHECK_BUDGET, **SN.search_check_verdict(new, stored),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(d / "result.json", res)
    print(f"RD CHECK-SEARCH {side} {'PASS' if res['passed'] else 'FAIL'}: {total} renders; mismatches "
          f"{res['mismatches']}")


# --- the floors, beside (renders) -------------------------------------------------------------------------------------

def cmd_floors(args):
    """Beside only (2 renders a distinct guitar a part; gates nothing): at the part's target preset, `xf-fix` and the
    four chain cells, each primed alone, judged on both halves against the record with the bank guitar as the judge's
    DI at lag 0; ln(d / d_Cen) on the held half, as `scratch_exact floors`. A guitar byte-identical to one already
    rendered for the part takes its result. On the checks' two parts `xn-list` is rendered again: its stored floor must
    repeat (render sha256 and both halves' distances). -> floors/<part>.json."""
    _guard_shard(args)
    m = require_rows(RD.PHASE_LADDER, RD.PHASE_FROZEN, RD.answers_key(NOW_ROW))
    why = row_refusal(FIX_ROW, m, stage1_record())        # floors sit beside xf-fix: only after stage 1 went on
    if why:
        raise SystemExit(why)
    xb = SE.require_xbuild(m)
    b2 = SE.bank_build(m)
    w = bench_world(m, FIX_ROW, b2, xb)
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import pipeline_fix as P

    R.no_separation_beside()
    draw, _sd = SE.context()
    repeat = set(SN.check_parts(draw["parts"]))
    lo, hi = SE._trim()
    LO._wait_cap()
    total, t0 = 0, time.time()
    for p in SE.mine(draw, args.shard):
        pk = p["pkey"]
        out = floor_path("floors", pk)
        if out.exists():
            continue
        SE.disk_guard()
        if pk in repeat:                                 # written once, like every other output (before any render)
            NT.never_overwrite(repeat_path(pk))
        t = json.loads(SE.target_path(pk).read_text())
        if t["record_file_sha256"] != S.file_sha(SE.record_path(pk)):
            raise SystemExit(f"{pk}: the record is not the target step's")
        ref = np.load(SE.record_path(pk)).astype(np.float64)
        dj = np.asarray(NT.load_dry(SE.BANK_ARM, pk, b2), np.float64)[lo:hi]
        xt = LO.tdict(t["target"])
        rec, done, renders = {"plan": PLAN, "part": pk, "guitars": {}}, {}, 0
        for g in FLOOR_ROWS + ((FLOOR_REPEAT,) if pk in repeat else ()):
            sha = guitar_sha(g, pk, w)
            if sha in done:
                rec["guitars"][g] = dict(done[sha][1], carried_from=done[sha][0])
                continue
            x32 = load_guitar(g, pk, w)
            y = np.asarray(AM.fresh_render(CB.new_renderer, x32, t["select"], xt, xt), np.float64)[lo:hi]
            renders += 2
            d = {h: (R.half_distance(ref, y, dj, 0, h) if np.isfinite(y).all() else math.inf) for h in K.R.HALVES}
            dh = d[p["held"]]
            res = {"d": d, "audio_sha256": AM.audio_sha(np.nan_to_num(y)), "dry_sha256": sha,
                   "floor": (math.log(dh / t["cen_held"]) if S.finite_pos(dh) else None), "zero": dh == 0.0}
            done[sha] = (g, res)
            rec["guitars"][g] = res
        if pk in repeat:
            st = json.loads(SE.floor_path("floors", pk).read_text())["guitars"][FLOOR_REPEAT]
            got = rec["guitars"][FLOOR_REPEAT]
            rec["xn_list_repeats"] = got["d"] == st["d"] and got["audio_sha256"] == st["audio_sha256"]
        total += renders
        rec.update(renders=renders, time=time.strftime("%Y-%m-%d %H:%M:%S"))
        P.save(out, rec)
        if pk in repeat:                                 # the flag alone: xf-fix's search never opens floors
            NT.never_overwrite(repeat_path(pk))
            P.save(repeat_path(pk), {"plan": PLAN, "part": pk, "xn_list_repeats": rec["xn_list_repeats"],
                                     "floor_sha256": S.file_sha(out)})
        print(f"{pk[-50:]}: floors {[(g, v['floor']) for g, v in rec['guitars'].items()]}"
              f"{'; xn-list repeats ' + str(rec['xn_list_repeats']) if pk in repeat else ''}; {total} renders",
              flush=True)
    print(f"RD FLOORS DONE {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s")


def cmd_floor_real(args):
    """The real floor, beside only (2 renders a part; gates nothing): row (b)'s stored answer through the `rf2` guitar,
    judged on the held half against the clean record with the true DI as the judge's DI at the part's lag;
    ln(d / Cen's stored value), and beside it the exact-notes test's stored real floors (the true DI, `tr-di`): rf2 less
    the true DI and rf2 less tr-di. An rf2 guitar byte-identical to tr-di takes tr-di's stored floor.
    -> floors-real/<part>.json."""
    _guard_shard(args)
    m = require_rows(*REAL_PHASES)
    why = row_refusal(REAL_ROW, m)
    if why:
        raise SystemExit(why)
    rb = fit_build(m, "real")
    b2 = SE.bank_build(m)
    w = {"real": rb, "b2": b2}
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import pipeline_fix as P

    R.no_separation_beside()
    draw, sd = SE.context()
    ans_b = S.require_hash(S.phase_answers(STEM_ROW), S.answers_path(STEM_ROW))
    lo, hi = SE._trim()
    LO._wait_cap()
    total, t0 = 0, time.time()
    for p in SE.mine(draw, args.shard):
        pk = p["pkey"]
        out = floor_path("floors-real", pk)
        if out.exists():
            continue
        SE.disk_guard()
        st = json.loads(SE.floor_path("floors-real", pk).read_text())
        sha = guitar_sha(REAL_ROW, pk, w)
        cen_stored = sd.cen_judge((p["set"], p["unit"], p["amp"]))[p["held"]]
        rec = {"plan": PLAN, "part": pk, "cen_stored": cen_stored, "dry_sha256": sha}
        if sha == guitar_sha(BASE, pk, w):
            rec[REAL_DRY] = dict(st[SE.BANK_ARM], carried_from=SE.BANK_ARM)
            renders = 0
        else:
            prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
            di32 = R.di_section(prt)
            di = np.asarray(di32, np.float64)[lo:hi]
            clean = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
            a = ans_b["parts"][pk]
            x = LO.tdict(a["answer"])
            y = np.asarray(AM.fresh_render(CB.new_renderer, load_guitar(REAL_ROW, pk, w), a["select"], x, x),
                           np.float64)[lo:hi]
            renders = 2
            dh = R.half_distance(clean, y, di, p["lag"], p["held"]) if np.isfinite(y).all() else math.inf
            rec[REAL_DRY] = {"held": dh, "audio_sha256": AM.audio_sha(np.nan_to_num(y)),
                             "ln_over_cen": math.log(dh / cen_stored) if S.finite_pos(dh) else None}
        mine_h = rec[REAL_DRY]["held"]
        for g in ("true", SE.BANK_ARM):
            rec[f"{REAL_DRY}_less_{g}"] = (math.log(mine_h / st[g]["held"])
                                          if S.finite_pos(mine_h) and S.finite_pos(st[g]["held"]) else None)
        total += renders
        rec.update(renders=renders, time=time.strftime("%Y-%m-%d %H:%M:%S"))
        P.save(out, rec)
        print(f"{pk[-50:]}: rf2 less true {rec[f'{REAL_DRY}_less_true']}; {total} renders", flush=True)
    print(f"RD FLOOR-REAL DONE {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s")


# --- the null build (zero renders) ------------------------------------------------------------------------------------

def cmd_null_build(_args):
    """Zero renders, once, only if the bench code asks (XF-part): per part X with the declared negligible change
    (`NULL_CHANGE`, `null_guitar`), refused if it equals X or is not finite; each file written once. -> dry/xf-null/,
    build-null.json (the search recomputes each guitar from X and checks it)."""
    m = require_rows(*bench_phases(NULL_ROW))
    why = row_refusal(NULL_ROW, m) or null_change_refusal(NULL_CHANGE)
    if why:
        raise SystemExit(why)
    NT.never_overwrite(null_build_path())
    import numpy as np

    from learn import pipeline_fix as P

    b2 = SE.bank_build(m)
    draw, _sd = SE.context()
    out = {"plan": PLAN, "row": NULL_ROW, "renders": 0, "change": NULL_CHANGE,
           "bank_build_sha256": S.file_sha(NT.build_path(SE.BUILD2)), "parts": {}}
    for p in draw["parts"]:
        pk = p["pkey"]
        x32 = NT.load_dry(SE.BANK_ARM, pk, b2)
        y32 = null_guitar(x32, NULL_CHANGE)
        if not np.isfinite(y32).all() or S.npy_sha(y32) == S.npy_sha(x32):
            raise SystemExit(f"{pk}: the null guitar equals X or is not finite: nothing written")
        out["parts"][pk] = {"files": {NULL_ROW: {"file_sha256": RD._write_once(guitar_path(NULL_ROW, pk), y32),
                                                 "audio_sha256": S.npy_sha(y32)}},
                            "x_sha256": S.npy_sha(x32)}
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(null_build_path(), out)
    print(f"RD NULL-BUILD: {len(out['parts'])} parts, change {NULL_CHANGE}; sha256 {S.file_sha(null_build_path())}")


def null_check(pk, w):
    """The null guitar recomputed from X (hashed build 2) with NULL_CHANGE must be the stored one."""
    want = guitar_sha(NULL_ROW, pk, w)
    if S.npy_sha(null_guitar(NT.load_dry(SE.BANK_ARM, pk, w["b2"]), NULL_CHANGE)) != want:
        raise SystemExit(f"{pk}: the null guitar is not X with NULL_CHANGE")


# --- the rows: search, answers, score ---------------------------------------------------------------------------------

def _source_path(src, pk):
    return SE.search_path(src, pk) if src in SE.ROWS else search_path(src, pk)


def cmd_search(args):
    """One shard of a row's searches (renders). Bench rows: per part (sorted by key, every n-th) the row's dry guitar
    (its sha256 the declared one), a guitar byte-identical to an earlier row's taking that record (and with `--rerun`
    its rerun) byte for byte (`carry_source`); else the record blanked outside the search half (records.json's sha256),
    `scratch_exact.start_reference` at lag 0, then `scratch_search.search_row_part` on `synthetic_part`. The real row:
    `_search_real`. The search opens nothing scored (`search_open`); the disk guard before every part."""
    row = args.row
    _guard_shard(args)
    if row == REAL_ROW:
        return _search_real(args)
    m = require_rows(*bench_phases(row))
    why = row_refusal(row, m, stage1_record() if row == FIX_ROW else None)
    if why:
        raise SystemExit(why)
    require_bench_checks("bench")
    xb = SE.require_xbuild(m)
    records = SE.require_records(m)
    if row == FIX_ROW:
        draw0, _ = SE.context()
        flags = {}
        for k in SN.check_parts(draw0["parts"]):
            fp = search_open(repeat_path(k))
            flags[k] = json.loads(fp.read_text()).get("xn_list_repeats") if fp.exists() else None
        why = floor_repeat_refusal(flags)
        if why:
            raise SystemExit(why)
    b2 = SE.bank_build(m)
    w = bench_world(m, row, b2, xb)
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import local_objective as LO
    from learn import note_replay as R

    R.no_separation_beside()
    draw, _sd = SE.context()
    todo = SE.mine(draw, args.shard)
    if getattr(args, "first", 0):
        todo = todo[:args.first]
    lists = C.mic_lists()
    LO._wait_cap()
    rerun = getattr(args, "rerun", False)
    total, carried, t0 = 0, 0, time.time()
    for p in todo:
        pk = p["pkey"]
        out = search_path(row, pk)
        if rerun:                                        # S1: a technical refusal, once more in this fresh process
            if not out.exists() or not S.refused_record(json.loads(out.read_text())):
                continue
            out = S.rerun_path(out)
        if out.exists():
            continue
        SE.disk_guard()
        sha = guitar_sha(row, pk, w)
        src = carry_source(row, sha, {r: guitar_sha(r, pk, w) for r in CARRY_FROM[row]})
        if src:
            sp = _source_path(src, pk)
            if rerun:
                sp = S.rerun_path(sp)
            if not sp.exists():
                raise SystemExit(f"{pk}: {row}'s guitar is {src}'s, and {src}'s record is not there yet")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(search_open(sp).read_bytes())
            carried += 1
            print(f"{pk[-50:]}: {row}'s guitar is byte-identical to {src}'s: its record taken byte for byte",
                  flush=True)
            continue
        if row == NULL_ROW:
            null_check(pk, w)
        x32 = load_guitar(row, pk, w)
        ref_blank = SE.load_record_blank(p, records)
        px = SE.synthetic_part(p)
        spath = start_path(row, pk)
        if rerun:
            spath = S.rerun_path(spath)
        sref, used = SE.start_reference(row, px, x32, ref_blank, CB.new_renderer, spath, sha)
        rec = S.search_row_part(px, row, SE.REF, x32, ref_blank, CB.new_renderer, lists, out, f"{LEDGER_ID} {RD.PHASE}",
                                start_ref=sref, dry_sha256=sha)
        total += rec.get("renders", 0) + used
        if "refused" in rec:
            print(f"{pk[-50:]}: REFUSED {rec['refused']}", flush=True)
        print(f"{row} shard {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s "
              f"({total / max(1, time.time() - t0) * 3600:.0f} an hour)", flush=True)
    print(f"RD SEARCH DONE {row} {args.shard[0]}/{args.shard[1]}: {total} renders, {carried} carried, in "
          f"{time.time() - t0:.0f} s")


def _carry_real(m, w, draw, sd):
    """`search --row fs-refit --carry` (2 renders a candidate), once, in one process before the bridge's search, as
    `scratch_notes.cmd_carry`: the candidates are the parts whose rf2 guitar is build 2's tr-di byte for byte and whose
    build 2 record is for it, not refused and not rerun (`carry_candidates`); every candidate's start reference is
    recomputed first (`scratch_notes.start_reference`, into this row's start-ref/, which the search then reuses); only
    if every one has build 2's render sha256 are their records copied byte for byte, else none is (`carry_all_or_none`).
    -> carry-real.json (never overwritten)."""
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    NT.never_overwrite(carry_path())
    by = {p["pkey"]: p for p in draw["parts"]}
    old_recs, reran = {}, set()
    for pk in by:
        op = SN.record_path("search", pk, REAL_FROM)
        if op.exists():
            old_recs[pk] = json.loads(search_open(op).read_text())
        if S.rerun_path(op).exists():
            reran.add(pk)
    new_parts = {pk: {"arms": {SN.DRY: {"sha256": guitar_sha(REAL_ROW, pk, w)}}} for pk in by}
    cands, skipped = SN.carry_candidates(new_parts, {pk: w["b2"]["parts"][pk] for pk in by}, old_recs, reran)
    for pk in cands:
        NT.never_overwrite(search_path(REAL_ROW, pk))
    LO._wait_cap()
    mine, theirs, renders = {}, {}, 0
    for pk in cands:
        SE.disk_guard()
        p, sha = by[pk], guitar_sha(REAL_ROW, pk, w)
        _, used = SN.start_reference(p, load_guitar(REAL_ROW, pk, w), S.load_ref_blank(sd, p, REAL_REF),
                                     CB.new_renderer, start_path(REAL_ROW, pk), sha)
        renders += used
        mine[pk] = json.loads(start_path(REAL_ROW, pk).read_text()).get("render_sha256")
        op = SN.record_path("start-ref", pk, REAL_FROM)
        theirs[pk] = json.loads(search_open(op).read_text()).get("render_sha256") if op.exists() else None
    carried, mism = carry_all_or_none(cands, mine, theirs)
    for pk in carried:
        dst = search_path(REAL_ROW, pk)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(search_open(SN.record_path("search", pk, REAL_FROM)).read_bytes())
    P.save(carry_path(), {"plan": PLAN, "row": REAL_ROW, "from": REAL_FROM, "renders": renders,
                          "build_real_sha256": S.file_sha(build_path("real")), "candidates": cands, "mismatches": mism,
                          "carried": carried, "not_carried": skipped,
                          "records_sha256": {pk: S.file_sha(search_path(REAL_ROW, pk)) for pk in carried},
                          "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    note = (f"none carried: {len(mism)} start-reference mismatch(es) ({mism}); every part is searched" if mism else
            f"{len(carried)} of {len(cands)} candidates carried")
    print(f"RD CARRY {REAL_FROM} -> {REAL_ROW}: {note}; {renders} renders")


def carry_record(rb_sha):
    """The bridge's carry record, refused unless it ran (`--carry`) on this build-real.json."""
    p = search_open(carry_path())
    if not p.exists():
        raise SystemExit("the bridge's carry has not run: `search --row fs-refit --carry` first (one process)")
    rec = json.loads(p.read_text())
    if rec.get("build_real_sha256") != rb_sha:
        raise SystemExit("carry-real.json was made from another build-real.json")
    return rec


def _search_real(args):
    """One shard of the bridge's searches (renders), as fs-notes' search with its own keys and folders. First, once,
    `--carry` (`_carry_real`, all or none). Then per part the rf2 guitar (its sha256 Unit 3's build-real's),
    `scratch_notes.start_reference` (the carry's, when it made one), `search_row_part` against `xlnoG@-3` blanked
    outside the search half; a carried part's record is already there and is skipped."""
    m = require_rows(*REAL_PHASES)
    why = row_refusal(REAL_ROW, m)
    if why:
        raise SystemExit(why)
    require_bench_checks("real")
    rb = fit_build(m, "real")
    b2 = SE.bank_build(m)
    w = {"real": rb, "b2": b2}
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import local_objective as LO
    from learn import note_replay as R

    R.no_separation_beside()
    draw, sd = SE.context()
    if getattr(args, "carry", False):
        if tuple(args.shard) != (0, 1):
            raise SystemExit("--carry runs once, in one process (no --shard)")
        return _carry_real(m, w, draw, sd)
    cr = carry_record(S.file_sha(build_path("real")))
    todo = SE.mine(draw, args.shard)
    if getattr(args, "first", 0):
        todo = todo[:args.first]
    lists = C.mic_lists()
    LO._wait_cap()
    rerun = getattr(args, "rerun", False)
    total, t0 = 0, time.time()
    for p in todo:
        pk = p["pkey"]
        out = search_path(REAL_ROW, pk)
        if rerun:
            if not out.exists() or not S.refused_record(json.loads(out.read_text())):
                continue
            out = S.rerun_path(out)
        if out.exists():
            continue
        SE.disk_guard()
        sha = guitar_sha(REAL_ROW, pk, w)
        x32 = load_guitar(REAL_ROW, pk, w)
        ref_blank = S.load_ref_blank(sd, p, REAL_REF)
        spath = start_path(REAL_ROW, pk)
        if rerun:
            spath = S.rerun_path(spath)
        sref, used = SN.start_reference(p, x32, ref_blank, CB.new_renderer, spath, sha)
        rec = S.search_row_part(p, REAL_DRY, REAL_REF, x32, ref_blank, CB.new_renderer, lists, out,
                                f"{LEDGER_ID} {RD.PHASE}", start_ref=sref, dry_sha256=sha)
        total += rec.get("renders", 0) + used
        if "refused" in rec:
            print(f"{pk[-50:]}: REFUSED {rec['refused']}", flush=True)
        print(f"{REAL_ROW} shard {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s",
              flush=True)
    print(f"RD SEARCH DONE {REAL_ROW} {args.shard[0]}/{args.shard[1]}: {total} renders ({len(cr['carried'])} carried "
          f"by --carry) in {time.time() - t0:.0f} s")


def cmd_answers(args):
    """A row's answers (zero renders): every search record or its passing rerun (`with_reruns`; one not yet rerun
    waits), each dry guitar the declared one (`scratch_exact.dry_refusal`); bench rows `xn_answer_parts` and T1's
    coverage, the real row `answer_parts` (borrowed answers and the centre) and `deciding_stop`; the refusals reported
    (S1), the carried parts named. -> answers-<row>.json; its sha256 into the ledger as `_answers_<row>` before
    `score`."""
    row = args.row
    m = require_rows(*row_phases(row))
    why = row_refusal(row, m, stage1_record() if row == FIX_ROW else None)
    if why:
        raise SystemExit(why)
    NT.never_overwrite(answers_path(row))
    from learn import pipeline_fix as P

    draw, _sd = SE.context()
    keys = [p["pkey"] for p in draw["parts"]]
    for k in keys:
        if not search_path(row, k).exists():
            raise SystemExit(f"{k}: not searched")
    recs, used, reruns = S.with_reruns(keys, lambda k: search_path(row, k))
    why = S.rerun_refusal(reruns)
    if why:
        raise SystemExit(why)
    b2 = SE.bank_build(m)
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    if row == REAL_ROW:
        w = {"real": fit_build(m, "real"), "b2": b2}
        checks = require_bench_checks("real")
    else:
        xb = SE.require_xbuild(m)
        w = bench_world(m, row, b2, xb)
        checks = require_bench_checks("bench")
    why = SE.dry_refusal(recs, {k: guitar_sha(row, k, w) for k in keys})
    if why:
        raise SystemExit(why)
    out = {"plan": PLAN, "row": row, "draw_sha256": S.file_sha(S.draw_path()),
           "time": time.strftime("%Y-%m-%d %H:%M:%S"),
           "renders": sum(r.get("renders", 0) for r in recs.values()), "reruns": reruns,
           "carried": {k: r.get("dry") for k, r in sorted(recs.items()) if r.get("dry") not in (row, REAL_DRY)},
           "checks_sha256": {kind: S.file_sha(check_dir("real" if row == REAL_ROW else "bench", kind) / "result.json")
                             for kind in checks}, "stopped": False}
    if row == REAL_ROW:
        parts, refused = S.answer_parts(draw, recs, lambda k: S.file_sha(used[k]))
        dec, pan, _stop = SN.deciding_stop(refused, sets_of)
        out.update(dry=REAL_DRY, ref=S.REF_NAME[REAL_REF], build_sha256=S.file_sha(build_path("real")),
                   refused_deciding=dec, refused_panel=pan)
    else:
        parts, refused = SE.xn_answer_parts(draw, recs, lambda k: S.file_sha(used[k]))
        tg = SE.require_targets(m)
        cov = {k: SE.coverage([s["module"] + "/" + s["key"] for s in (recs[k].get("searched_dims") or [])],
                              tg["parts"][k]["changed"]) for k in parts}
        out.update(ref=SE.REF, build_sha256=S.file_sha(SE.build_path()), ladder_sha256=S.file_sha(RD.ladder_path()),
                   coverage={"covered": sum(c["covered"] for c in cov.values()), "parts": cov})
        for kind in ("bench", "null"):
            if kind in w:
                out[f"{kind}_build_sha256"] = S.file_sha(build_path("bench") if kind == "bench" else null_build_path())
    out.update(refused=refused, refusal_report=S.refusal_report(refused, sets_of, RD.DECIDING), parts=parts)
    P.save(answers_path(row), out)
    print(f"RD ANSWERS {row}: {len(parts)} parts, {len(refused)} refused (each reads at Cen); {len(out['carried'])} "
          f"carried; reruns {reruns}; sha256 {S.file_sha(answers_path(row))} (into the ledger as {RD.answers_key(row)} "
          "before `score`)")


def cmd_score(args):
    """One shard of a row's score (renders), from its hashed answers. Bench rows: Cen and the five settings through the
    bank guitar, each primed alone, judged on the held half against the record at lag 0
    (`scratch_exact.score_exact_part`), the scoring control against Cen's value from `targets`. The real row:
    `scratch_search.score_row_part` (through the true DI, against the clean record). -> score/<row>/<part>.json."""
    row = args.row
    _guard_shard(args)
    m = require_rows(*row_phases(row), RD.answers_key(row))
    why = row_refusal(row, m, stage1_record() if row == FIX_ROW else None)
    if why:
        raise SystemExit(why)
    ans = NT.require_file_hash(m, RD.answers_key(row), answers_path(row))
    asha = S.file_sha(answers_path(row))
    b2 = SE.bank_build(m)
    if row != REAL_ROW:
        records = SE.require_records(m)
        tg = SE.require_targets(m)
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import pipeline_fix as P

    R.no_separation_beside()
    draw, sd = SE.context()
    LO._wait_cap()
    total, t0 = 0, time.time()
    for p in SE.mine(draw, args.shard):
        pk = p["pkey"]
        out = score_path(row, pk)
        a = ans["parts"].get(pk)
        if getattr(args, "rerun", False):                # S1: a scoring-control miss, once more in this fresh process
            if a is None or not out.exists() or json.loads(out.read_text())["scoring_control_ok"]:
                continue
            out = S.rerun_path(out)
        if a is None or out.exists():
            continue
        SE.disk_guard()
        if row == REAL_ROW:
            rec, used = S.score_row_part(p, a, ans["parts"], REAL_ROW, asha, sd, CB.new_renderer)
        else:
            bank32 = NT.load_dry(SE.BANK_ARM, pk, b2)
            ref = SE.load_record(pk, records)
            rec, used = SE.score_exact_part(SE.synthetic_part(p), a, bank32, ref, 0, tg["parts"][pk]["cen_held"],
                                            CB.new_renderer)
            rec.update(row=row, answers_sha256=asha)
        total += used
        P.save(out, rec)
        print(f"{pk[-50:]}: scored {rec['distinct_renders']} settings; control "
              f"{'ok' if rec['scoring_control_ok'] else 'MISS'}; {total} renders, {time.time() - t0:.0f} s", flush=True)
    print(f"RD SCORE DONE {row} {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s")


# --- the reads (zero renders) -----------------------------------------------------------------------------------------

def bench_parts(draw, ans, answers_sha, score_file):
    """A bench row's per-part numbers from its score files, as `scratch_exact.read_xn_parts` reads them: a
    scoring-control miss read from its rerun (S1; one not yet rerun waits), then a refusal; `deciding_bug` stops the
    read; `nonfinite_rule`; `xn_numbers`. score_file(pkey) -> path. -> (per, refused, replaced, misses)."""
    refused = dict(ans["refused"])
    per, replaced, ctl = {}, {}, []
    for p in draw["parts"]:
        k = p["pkey"]
        if k not in ans["parts"]:
            per[k] = None
            continue
        sp = score_file(k)
        if not sp.exists():
            raise SystemExit(f"{k}: not scored")
        sc = json.loads(sp.read_text())
        if not sc["scoring_control_ok"]:
            if not S.rerun_path(sp).exists():
                raise SystemExit(f"{k}: a scoring-control miss not yet rerun: `score --rerun` first")
            again = json.loads(S.rerun_path(sp).read_text())
            if again["scoring_control_ok"]:
                sc = again
        if sc["answers_sha256"] != answers_sha:
            raise SystemExit(f"{k}: scored from other answers")
        if not sc["scoring_control_ok"]:
            refused[k] = {"scoring_control": {"cen": sc["held"]["cen"], "stored": sc["cen_stored"]}}
            ctl.append(k)
            per[k] = None
            continue
        bug = SE.deciding_bug(sc["held"])
        if bug:
            raise SystemExit(f"{k}: {bug}: a zero or non-finite distance on a deciding setting is a bug: the read "
                             "stops, to the user")
        held, rep = S.nonfinite_rule(sc["held"])
        if rep:
            replaced[k] = rep
        per[k] = SE.xn_numbers(held)
    return per, refused, replaced, ctl


def _numbers(per, refused, replaced, ctl, sha, fields=SE.FIELDS, extra=None):
    return dict({"per": per, "itt": S.itt_per(per, refused, fields), "refused": refused, "replaced": replaced,
                 "control_misses": ctl, "answers_sha256": sha}, **(extra or {}))


def bench_numbers(m, draw, row):
    """A bench row's numbers (the exact-notes test's rows from their hashed answers and score files, this module's from
    its own). -> {per, itt (S1), refused, replaced, control_misses, answers_sha256}."""
    if row in SE.ROWS:
        key, path, sf = SE.answers_key(row), SE.answers_path(row), (lambda k: SE.score_path(row, k))
    else:
        key, path, sf = RD.answers_key(row), answers_path(row), (lambda k: score_path(row, k))
    ans = NT.require_file_hash(m, key, path)
    sha = S.file_sha(path)
    return _numbers(*bench_parts(draw, ans, sha, sf), sha, extra={"coverage": ans.get("coverage"),
                                                                 "carried": ans.get("carried")})


def real_numbers(m, draw, sd, row):
    """A real row's numbers through `scratch_search.read_row_parts`: row (b), row (c), build 2 or the bridge, each
    from its hashed answers and score files."""
    from learn import note_replay as R

    if row == STEM_ROW or row == BOTH_ROW:
        path = S.answers_path(row)
        ans = S.require_hash(S.phase_answers(row), path)
        sf = (lambda k: S.score_path(row, k))
    elif row == REAL_FROM:
        path = SN.answers_path(REAL_FROM)
        ans = NT.require_file_hash(m, SE.PHASE_B2_ANSWERS, path)
        sf = (lambda k: SN.score_path(k, REAL_FROM))
    elif row == REAL_ROW:
        path = answers_path(REAL_ROW)
        ans = NT.require_file_hash(m, RD.answers_key(REAL_ROW), path)
        sf = (lambda k: score_path(REAL_ROW, k))
    else:
        raise ValueError(row)
    sha = S.file_sha(path)
    rby = {p["pkey"]: p for p in R.require_draw()["parts"]}
    return _numbers(*S.read_row_parts(draw, ans, sha, sf, sd, rby), sha, fields=S.G_FIELDS)


def the_40(sd, draw, vals, keys=None):
    """BKS+GOAT's pooled interval on the 40 (`scratch_notes.set_rows`), or None."""
    return ((SN.set_rows(sd, draw, vals, keys) or {}).get("bks_goat") or {}).get("all")


def split_keys(draw, tg, xb, b2, list_answers):
    """The splits' part sets: one part per partner (the exact-notes targets' partners), without the two design-time
    parts, the tilt parts of the 40 and the rest of the 40, and the clusters of the 40."""
    deciding = sorted(p["pkey"] for p in draw["parts"] if p["set"] in RD.DECIDING)

    def tilt(rep):
        t = (rep or {}).get("tilt") or {}
        return t.get("tilt_db_s") if t.get("applied") else None
    t_list = {k: tilt(xb["parts"][k]["guitars"][LIST_ROW].get("report")) for k in xb["parts"]}
    t_x = {k: tilt(b2["parts"][k]["arms"][SE.BANK_ARM].get("report")) for k in b2["parts"]}
    tilt15 = tilt_parts({k: t_list.get(k) is not None for k in deciding}, deciding)
    clusters = {}
    for p in draw["parts"]:
        if p["set"] in RD.DECIDING:
            clusters.setdefault(p["cluster"], []).append(p["pkey"])
    return {"one_per_partner": SE.one_per_partner({k: t["partner"] for k, t in tg["parts"].items()}),
            "design_time": design_time_parts(sorted(list_answers["refused"]), t_x, t_list, deciding),
            "tilt": tilt15, "rest": sorted(set(deciding) - set(tilt15)), "deciding": deciding,
            "clusters": [sorted(v) for _, v in sorted(clusters.items())]}


def _iv(r):
    return {q: (r or {}).get(q) for q in ("mean", "lo90", "hi90")} if r else None


def splits(sd, draw, vals, groups, full=True):
    """One paired figure on the declared splits: the 40 (deciding), clean and crunch, all 47 and the panel, and with
    `full` each cluster of the 40 left out, one part per partner, without the two design-time parts, and the tilt parts
    against the rest of the 40 (subset intervals and contributions to the 40's mean; labelled seen)."""
    r = SN.set_rows(sd, draw, vals)
    bg = (r or {}).get("bks_goat") or {}
    out = {"the_40": bg.get("all"), "clean": bg.get("clean"), "crunch": bg.get("crunch"),
           "all_47": (r or {}).get("deciding_pool"), "panel": _iv((r or {}).get("panel")),
           "per_set": {s: _iv((r or {}).get(s)) for s in S.SETS} if r else None,
           "leave_one_cluster_out_per_set": (r or {}).get("leave_one_cluster_out"),
           "parts": len([v for v in vals.values() if v is not None])}
    if not full:
        return out
    out["cluster_left_out"] = [the_40(sd, draw, vals, set(groups["deciding"]) - set(c)) for c in groups["clusters"]]
    means = [x["mean"] for x in out["cluster_left_out"] if x and x.get("mean") is not None]
    out["cluster_left_out_range"] = [min(means), max(means)] if means else None
    keep_opp = set(groups["one_per_partner"])
    n_all, n_40 = len(keep_opp & set(vals)), len(keep_opp & set(vals) & set(groups["deciding"]))
    out["one_per_partner"] = {"parts_all_47": n_all, "parts_on_the_40": n_40, "iv": the_40(sd, draw, vals, keep_opp),
                              "label": f"one part per partner: {n_all} parts over all 47, {n_40} of them on the 40 "
                                       "(the interval is the 40's pool on those)"}
    keep = set(vals) - set(groups["design_time"])
    out["without_design_time"] = {"parts_left_out": len(groups["design_time"]), "iv": the_40(sd, draw, vals, keep)}
    tilt, rest = set(groups["tilt"]), set(groups["rest"])
    out["tilt_15_vs_25"] = {"label": SEEN_LABEL, "tilt_parts": len(tilt), "rest_parts": len(rest),
                            "tilt": the_40(sd, draw, vals, tilt), "rest": the_40(sd, draw, vals, rest),
                            "tilt_contribution": the_40(sd, draw, contributions(vals, tilt)),
                            "rest_contribution": the_40(sd, draw, contributions(vals, rest))}
    return out


def figure(sd, draw, new, old, groups):
    """A paired figure G(new) - G(old) on every arm: the answer on every split, the shrunk arm and the checkpoints on
    the 40, clean, crunch and all 47; each arm's `paired_reading` on the 40."""
    out = {}
    for arm, f in ARMS.items():
        s = splits(sd, draw, SN.paired_values(new, old, f), groups, full=(arm == DECIDING_ARM))
        s["reading"] = SN.paired_reading(s["the_40"])
        out[arm] = s
    return out


def own_g(sd, draw, itt):
    """A row's own G (ln(answer / Cen)) on the 40 with `number_reading`."""
    iv = the_40(sd, draw, {k: v["G"] for k, v in itt.items() if v and v.get("G") is not None})
    return {"iv": iv, "reading": S.number_reading(iv)}


def _close(iv, seen):
    return bool(iv) and all(round(iv[k], 3) == v for k, v in zip(("mean", "lo90", "hi90"), seen))


def reproduce(m, draw, sd):
    """Zero renders: D_list (G(xn-list) - G(xn-bank), S1) and build 2 less row (b) on the 40 through this module's
    read (`bench_numbers`, `real_numbers`, `the_40`), equal to the exact-notes read's stored rows exactly and to the
    declared figures to 3 places (D_list +0.321 [+0.180, +0.462]; build 2 less row (b) +0.274 [+0.186, +0.361]).
    -> {figures, exact, seen, holds}."""
    bank, lst = bench_numbers(m, draw, BASE), bench_numbers(m, draw, LIST_ROW)
    rb, rn = real_numbers(m, draw, sd, STEM_ROW), real_numbers(m, draw, sd, REAL_FROM)
    got = {"D_list": the_40(sd, draw, SN.paired_values(lst["itt"], bank["itt"], "G")),
           "b2_less_row_b": the_40(sd, draw, SN.paired_values(rn["itt"], rb["itt"], "G"))}
    stored = json.loads(SE.rows_path().read_text())["rows"]
    want = {"D_list": stored["arms"]["answer"]["D"]["D_list"]["bks_goat"]["all"],
            "b2_less_row_b": stored["beside"]["answer"]["real_gap"]["bks_goat"]["all"]}
    exact = {n: bool(got[n]) and all(got[n][q] == want[n][q] for q in ("mean", "lo90", "hi90")) for n in got}
    seen = {n: _close(got[n], SEEN[n]) for n in got}
    return {"figures": got, "stored": want, "exact": exact, "seen": seen,
            "holds": all(exact.values()) and all(seen.values())}


def require_reproduced(m, draw, sd):
    r = reproduce(m, draw, sd)
    if not r["holds"]:
        raise SystemExit(f"the read does not reproduce the stored figures ({r['exact']}, {r['seen']}): a bug, to the "
                         "user")
    return r


def _passing(nums):
    return any(n["refused"] for n in nums.values())


def _refusals(nums, sets_of):
    return {r: {"refused": n["refused"], "report": S.refusal_report(n["refused"], sets_of, RD.DECIDING),
                "control_misses": n["control_misses"], "nonfinite_replaced": n["replaced"]} for r, n in nums.items()}


def floors_beside(sd, draw):
    """The bench floors (beside, gating nothing) when every part's file is there: per guitar ln(d / d_Cen) on the 40
    and all 47, and whether the stored xn-list floor repeated on the checks' parts."""
    keys = sorted(p["pkey"] for p in draw["parts"])
    if not all(floor_path("floors", k).exists() for k in keys):
        return None
    fl = {k: json.loads(floor_path("floors", k).read_text()) for k in keys}
    out = {g: {"the_40": the_40(sd, draw, {k: fl[k]["guitars"][g]["floor"] for k in keys}),
               "zero_parts": sum(fl[k]["guitars"][g]["zero"] for k in keys)} for g in FLOOR_ROWS}
    out["xn_list_repeats"] = {k: r["xn_list_repeats"] for k, r in fl.items() if "xn_list_repeats" in r}
    out["renders"] = sum(r["renders"] for r in fl.values())
    return out


def cmd_read(args):
    """The bench read (zero renders), once a stage. `--stage 1` (after xf-now's score): D_now = G(xf-now) - G(xn-bank)
    on every arm and split, D_list - D_now beside, `xf_stage1`'s code with S1, then the go record xf-fix's search reads.
    `--stage 2` (after xf-fix's): D_now, D_fix, the gain (G(xf-fix) - G(xf-now)), `xf_read`'s code with S1, the floors
    beside. `--stage rungs`: each rung or null row run, against xn-bank and against xf-now, beside (no code). The rows
    are saved before the code; the stored figures are reproduced first. -> rows-<stage>.json, report-<stage>.json."""
    stage = str(getattr(args, "stage", "1") or "1")
    if stage not in ("1", "2", "rungs"):
        raise SystemExit("--stage 1, 2 or rungs")
    base = (SE.answers_key(BASE), SE.answers_key(LIST_ROW), SE.PHASE_B2_ANSWERS, RD.PHASE_LADDER,
            RD.answers_key(NOW_ROW))
    if stage == "1":
        m = require_rows(*base)
        rows_run, name = (NOW_ROW,), "stage1"
    elif stage == "2":
        m = require_rows(*base, RD.PHASE_FROZEN, RD.answers_key(FIX_ROW))
        rows_run, name = (NOW_ROW, FIX_ROW), "stage2"
    else:
        m = require_rows(*base, RD.PHASE_BENCH_OUTCOME)
        rows_run = (NOW_ROW,) + tuple(r for r in RUNG_ROWS + (NULL_ROW,) if RD.answers_key(r) in m)
        if len(rows_run) == 1:
            raise SystemExit("no rung or null row's answers on main")
        name = "rungs-" + "+".join(RD.SHORT[r] for r in rows_run[1:])
    for p_ in (read_path("rows", name), read_path("report", name)) + ((stage1_path(),) if stage == "1" else ()):
        NT.never_overwrite(p_)
    from learn import pipeline_fix as P

    draw, sd = SE.context()
    repro = require_reproduced(m, draw, sd)
    xb = SE.require_xbuild(m)
    tg = SE.require_targets(m)
    b2 = SE.bank_build(m)
    nums = {r: bench_numbers(m, draw, r) for r in (BASE, LIST_ROW) + rows_run}
    groups = split_keys(draw, tg, xb, b2, json.loads(SE.answers_path(LIST_ROW).read_text()))
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    it = {r: n["itt"] for r, n in nums.items()}
    pr = {r: n["per"] for r, n in nums.items()}
    passing = _passing(nums)
    D = {"D_now": figure(sd, draw, it[NOW_ROW], it[BASE], groups),
         "D_list_less_D_now": figure(sd, draw, it[LIST_ROW], it[NOW_ROW], groups)}
    if stage == "2":
        D["D_fix"] = figure(sd, draw, it[FIX_ROW], it[BASE], groups)
        D["gain"] = figure(sd, draw, it[FIX_ROW], it[NOW_ROW], groups)
    if stage not in ("1", "2"):
        for r in rows_run[1:]:
            D[f"D_{RD.SHORT[r]}"] = figure(sd, draw, it[r], it[BASE], groups)
            D[f"{RD.SHORT[r]}_less_now"] = figure(sd, draw, it[r], it[NOW_ROW], groups)
    body = {"plan": PLAN, "stage": stage, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "renders": 0,
            "rows_read": list(rows_run), "reproduce": repro, "groups_sizes": {k: len(v) for k, v in groups.items()},
            "answers_sha256": {r: n["answers_sha256"] for r, n in nums.items()},
            "refusals": _refusals(nums, sets_of), "carried": {r: nums[r].get("carried") for r in rows_run},
            "own_g": {r: own_g(sd, draw, it[r]) for r in nums}}
    if stage == "2":
        body["floors"] = floors_beside(sd, draw)
    pD = None
    if passing:
        pD = {"D_now": the_40(sd, draw, SN.paired_values(pr[NOW_ROW], pr[BASE], "G"))}
        if stage == "2":
            pD["D_fix"] = the_40(sd, draw, SN.paired_values(pr[FIX_ROW], pr[BASE], "G"))
            pD["gain"] = the_40(sd, draw, SN.paired_values(pr[FIX_ROW], pr[NOW_ROW], "G"))
    rows = {"D": D, "passing_only": pD}
    P.save(read_path("rows", name), dict(body, rows=rows))     # the rows are saved before the code is read
    report = dict(body, rows=rows)
    a = {n: v[DECIDING_ARM]["the_40"] for n, v in D.items()}
    sh = {n: v["shrunk"]["the_40"] for n, v in D.items()}
    if stage == "1":
        code, cp, label = with_passing(RD.xf_stage1, (a["D_now"],), (pD["D_now"],) if pD else None)
        report.update(xf=code, code=code.get("code"), go_on=code["go_on"], passing_only=cp, label=label,
                      shrunk=RD.xf_stage1(sh["D_now"]),
                      next="to the user with both reads" if label else code["next"])
        P.save(read_path("report", name), report)
        P.save(stage1_path(), {"plan": PLAN, "code": code.get("code"), "go_on": bool(code["go_on"]) and not label,
                               "label": label, "answers_now_sha256": nums[NOW_ROW]["answers_sha256"],
                               "report_sha256": S.file_sha(read_path("report", name))})
    elif stage == "2":
        code, cp, label = with_passing(RD.xf_read, (a["D_now"], a["D_fix"], a["gain"]),
                                       (pD["D_now"], pD["D_fix"], pD["gain"]) if pD else None)
        report.update(xf=code, code=code.get("code"), passing_only=cp, label=label,
                      shrunk=RD.xf_read(sh["D_now"], sh["D_fix"], sh["gain"]),
                      next="to the user with both reads" if label else code["next"])
        P.save(read_path("report", name), report)
    else:
        report.update(code=None, next="beside: the rung and null rows price the residual; to the user")
        P.save(read_path("report", name), report)
    for n, iv in a.items():
        print(f"{n} on the 40: {iv} -> {(D[n][DECIDING_ARM]['reading'] or {}).get('reading')}")
    print(f"RD READ stage {stage}: {report.get('code')} {('(' + report['label'] + ')') if report.get('label') else ''}"
          f"; next: {report['next']}; sha256 {S.file_sha(read_path('report', name))}")


def cmd_read_real(_args):
    """The bridge's read (zero renders), once: per part (S1) G(fs-refit), build 2, row (b) and row (c); D_real =
    G(fs-refit) - G(build 2) and G(fs-refit) - G(row (b)), G(fs-refit) - G(row (c)) beside, on every arm and split;
    `rf_code` with S1; the real floor beside (gating nothing). The stored figures are reproduced first.
    -> rows-real.json, report-real.json."""
    m = require_rows(*REAL_PHASES, RD.answers_key(REAL_ROW), S.phase_answers(STEM_ROW), S.phase_answers(BOTH_ROW),
                     SE.answers_key(BASE), SE.answers_key(LIST_ROW))
    why = row_refusal(REAL_ROW, m)
    if why:
        raise SystemExit(why)
    for p_ in (read_path("rows", "real"), read_path("report", "real")):
        NT.never_overwrite(p_)
    from learn import pipeline_fix as P

    draw, sd = SE.context()
    repro = require_reproduced(m, draw, sd)
    xb = SE.require_xbuild(m)
    tg = SE.require_targets(m)
    b2 = SE.bank_build(m)
    groups = split_keys(draw, tg, xb, b2, json.loads(SE.answers_path(LIST_ROW).read_text()))
    nums = {r: real_numbers(m, draw, sd, r) for r in (REAL_ROW, REAL_FROM, STEM_ROW, BOTH_ROW)}
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    it = {r: n["itt"] for r, n in nums.items()}
    pr = {r: n["per"] for r, n in nums.items()}
    D = {"D_real": figure(sd, draw, it[REAL_ROW], it[REAL_FROM], groups),
         "vs_row_b": figure(sd, draw, it[REAL_ROW], it[STEM_ROW], groups),
         "vs_row_c": figure(sd, draw, it[REAL_ROW], it[BOTH_ROW], groups),
         "b2_less_row_b": figure(sd, draw, it[REAL_FROM], it[STEM_ROW], groups)}
    keys = sorted(sets_of)
    fr = {k: json.loads(floor_path("floors-real", k).read_text()) for k in keys
          if floor_path("floors-real", k).exists()}
    floor = None
    if len(fr) == len(keys):
        floor = {"label": "beside only; gates nothing",
                 "ln_over_cen": the_40(sd, draw, {k: r[REAL_DRY]["ln_over_cen"] for k, r in fr.items()}),
                 "less_true": the_40(sd, draw, {k: r[f"{REAL_DRY}_less_true"] for k, r in fr.items()}),
                 "less_tr_di": the_40(sd, draw, {k: r[f"{REAL_DRY}_less_{SE.BANK_ARM}"] for k, r in fr.items()})}
    pD = None
    if _passing(nums):
        pD = {"vs_row_b": the_40(sd, draw, SN.paired_values(pr[REAL_ROW], pr[STEM_ROW], "G")),
              "D_real": the_40(sd, draw, SN.paired_values(pr[REAL_ROW], pr[REAL_FROM], "G"))}
    body = {"plan": PLAN, "row": REAL_ROW, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "renders": 0,
            "reproduce": repro, "answers_sha256": {r: n["answers_sha256"] for r, n in nums.items()},
            "refusals": _refusals(nums, sets_of), "own_g": {r: own_g(sd, draw, it[r]) for r in nums},
            "real_floor": floor}
    rows = {"D": D, "passing_only": pD}
    P.save(read_path("rows", "real"), dict(body, rows=rows))   # the rows are saved before the code is read
    a = {n: v[DECIDING_ARM]["the_40"] for n, v in D.items()}
    code, cp, label = with_passing(RD.rf_code, (a["vs_row_b"], a["D_real"]),
                                   (pD["vs_row_b"], pD["D_real"]) if pD else None)
    sh = {n: v["shrunk"]["the_40"] for n, v in D.items()}
    report = dict(body, rows=rows, rf=code, code=code["code"], passing_only=cp, label=label,
                  shrunk=RD.rf_code(sh["vs_row_b"], sh["D_real"]),
                  next="to the user with both reads" if label else code["next"])
    P.save(read_path("report", "real"), report)
    for n, iv in a.items():
        print(f"{n} on the 40: {iv}")
    print(f"RD READ-REAL {code['code']}{' (' + label + ')' if label else ''}: {code['reading']}. "
          f"Next: {report['next']}")


def cmd_reproduce(_args):
    """Zero renders: `reproduce` from the stored files, printed and saved (never overwritten)."""
    m = require_rows(SE.answers_key(BASE), SE.answers_key(LIST_ROW), SE.PHASE_B2_ANSWERS, S.phase_answers(STEM_ROW))
    NT.never_overwrite(reproduce_path())
    from learn import pipeline_fix as P

    draw, sd = SE.context()
    r = reproduce(m, draw, sd)
    P.save(reproduce_path(), dict(r, plan=PLAN, renders=0, time=time.strftime("%Y-%m-%d %H:%M:%S")))
    for n, iv in r["figures"].items():
        print(f"{n} on the 40: {iv}; exact {r['exact'][n]}; seen {r['seen'][n]}")
    print(f"RD REPRODUCE {'HOLDS' if r['holds'] else 'FAILS'}")


COMMANDS = {"check-score": cmd_check_score, "check-search": cmd_check_search, "floors": cmd_floors,
            "floor-real": cmd_floor_real, "null-build": cmd_null_build, "search": cmd_search, "answers": cmd_answers,
            "score": cmd_score, "read": cmd_read, "read-real": cmd_read_real, "reproduce": cmd_reproduce}
NEEDS_ROW = ("search", "answers", "score")


def main(argv=None):
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    for p_ in (str(root), str(root / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--row", choices=ROWS)
    ap.add_argument("--shard", type=S._shard, default=(0, 1))
    ap.add_argument("--first", type=int, default=0, help="search only this shard's first n parts (the re-timing)")
    ap.add_argument("--rerun", action="store_true",
                    help="search or score again, once, only the parts whose record refused (S1: then Cen)")
    ap.add_argument("--stage", choices=("1", "2", "rungs"), default="1", help="read: the bench read's stage")
    ap.add_argument("--carry", action="store_true",
                    help="search --row fs-refit: build 2's records carried, all or none, once before the search")
    ap.add_argument("--for", dest="side", choices=("bench", "real"), default="bench",
                    help="check-score, check-search: the bench's path or the bridge's")
    args = ap.parse_args(argv)
    if args.cmd in NEEDS_ROW and not args.row:
        ap.error(f"{args.cmd} needs --row")
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
