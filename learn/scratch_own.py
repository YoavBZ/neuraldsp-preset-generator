"""The `vc-own` search row, `fs-own` (`docs/scratch-own-plan.md`; ledger `preset-ladder` `phase_scratch_own`, then
`phase_scratch_own_answers` and `phase_scratch_own_outcome`): what real audio inside our note windows buys, by
search.

The row repeats build 2's search (`fs-notes` b2) with one change: the dry guitar is the stored `vc-own` (the true DI's
raw section gated by our played notes, through the part's own finish, at -22.9 LUFS; `learn/voice_build.py`, hashed in
`phase_scratch_voice_dry`) instead of `tr-di`. The reference is `xlnoG@-3` blanked outside the search half, as rows
(b), (c), build 2 and `fs-refit`; the search sees the stem, never the real record.

| Row | Dry guitar | Reference on the search half |
|---|---|---|
| row (b) `fs-stem` | the true DI | `xlnoG@-3` |
| build 2 (`fs-notes` b2) | `tr-di` | `xlnoG@-3` |
| `fs-own` | `vc-own` | `xlnoG@-3` |

    $MAIN -m learn.scratch_own check-score              # row (c) re-scored through score_row_part (about 40 renders)
    $MAIN -m learn.scratch_own check-search             # row (c)'s first 10 evaluations (about 22 renders)
    $MAIN -m learn.scratch_own search --shard k/3 [--rerun]
    $MAIN -m learn.scratch_own answers                  # zero renders -> phase_scratch_own_answers (hash PR first)
    $MAIN -m learn.scratch_own score --shard k/3 [--rerun]
    $MAIN -m learn.scratch_own reproduce                # zero renders: build 2 less row (b), LOUDAR's stored G50
    $MAIN -m learn.scratch_own read                     # zero renders, once: D_own, C_own, XW_TABLE's code

**Mechanics, unchanged code.** It mirrors `rederive_rows`' `fs-refit` (`_search_real`, `cmd_answers`, `cmd_score`, the
checks) and calls the shared steps unchanged: `scratch_notes.start_reference`, `scratch_search.search_row_part` with
`dry_sha256`, `answer_parts`, `scratch_notes.deciding_stop`, `score_row_part`, `read_row_parts`; the same draw, halves,
Cen, partners, seeds, 200-evaluation step 1 and step 2. Only the guitar, its sha256, the row's name and the paths
differ (a fake-world test holds it). The guitar is `PF/fs/voice/dry/vc-own/<part>.npy` handed as stored: its file and
its samples must be build.json's (`file_sha256`, `audio_sha256`), and build.json's sha256 main's
`phase_scratch_voice_dry`. No carry: a `vc-own` byte-identical to a searched guitar (the true DI, `tr-di`, `avg+mild`,
`rf2`) stops, to the orchestrator. The judge's frame mask in the search moves with the dry guitar (`aligned_distance`
is handed the dry guitar), as it did between row (b) and build 2; it is part of "the dry guitar".

**The score.** Cen, the answer, cp50, cp100, cp200, the shrunk answer and the borrowed answers through the true DI,
judged on the held half against the clean record (`score_row_part`).

**S1.** A technical refusal reruns once (`--rerun`, a fresh process), then reads at Cen (`deciding_stop` reports it);
the passing-only read sits beside, and the code is `refusal-sensitive` when the two differ.

**The numbers** (per part, paired; the 40 decide by `scratch_notes.set_rows`, the answer arm): D_own = G(fs-own) -
G(build 2); C_own = G(fs-own) - G(row (b)). `XW_TABLE` reads `paired_reading` of D_own, of -D_own (build 2 against the
row, where "matches" rules a heard-size gain out) and of C_own, the first that holds. Beside, never changing the code:
the shrunk arm's code (`shrunk-sensitive` when it differs) and the checkpoints'; LOUDAR (G at cp50 of `fs-own` less
`ld-stem`'s G50 on BKS+panel, `scratch_loudar.bp_rows`, the part-weighted mean beside, read both ways); Fieller's share
-D_own / (build 2 - row (b)); each cluster left out, the three largest parts, clean, crunch, all 47, the panel, one part
per partner; against row (c); the stored S and the control's Ux per part against -D_own (Spearman).

**The gate.** Every render command checks the control's audited code itself (`phase_scratch_voice_control_outcome`;
refused when absent; XC-anomaly, an undeclared code, or XC-part or XC-notes without `coverage_label` stops: it fails
closed, as `spend_refusal` since #658) and then calls `scratch_voice.require_spend("search-row")` and relies on it:
under XC-notes, or XC-part marked `coverage-sensitive`, the spend gate opens only with the user's renewed word in
`phase_scratch_voice_waiver` (`answers_code` the control's code, `date` on or after the control outcome's,
`spend_kinds` holding "search-row"); XC-stands, plain XC-part and XC-undecided go on the user's 2026-11-28 go.
The row keeps no word of its own (the control's review, 2026-11-28).

Every command refuses unless this checkout runs main's code (this module and `PINNED`) and keys (the
`phase_scratch_own*` and `phase_scratch_voice*` keys), and main holds the keys it reads. The search opens nothing
scored (`search_open`: `rederive_rows`' forbidden files and this module's own, amendment 6).

The pure parts (`XW_TABLE`, `xw_code`, the gate, the forbidden paths, the shard rule, the guards) are tested in
tests/test_scratch_own.py on the light CI runner (no numpy at import); the commands behind fakes.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics
import time

from learn import note_transcribe as NT
from learn import rederive_rows as RR
from learn import scratch_exact as SE
from learn import scratch_loudar as SL
from learn import scratch_notes as SN
from learn import scratch_rederive as RD
from learn import scratch_search as S
from learn import scratch_voice as SV

LEDGER_ID = S.LEDGER_ID                  # preset-ladder
PLAN = "docs/scratch-own-plan.md"
KEY_PREFIX = "phase_scratch_own"
PHASE = KEY_PREFIX                       # this declaration
PHASE_ANSWERS = f"{KEY_PREFIX}_answers"  # the hash PR: answers.json's sha256, before any score
PHASE_OUTCOME = f"{KEY_PREFIX}_outcome"  # the audited read
KEYS_TO_COME = (PHASE_ANSWERS, PHASE_OUTCOME)
GUARDED_PREFIXES = SV.GUARDED_PREFIXES + (SV.KEY_PREFIX, SL.KEY_PREFIX)

MODULE = "learn/scratch_own.py"
PINNED = ("learn/scratch_search.py", "learn/scratch_notes.py", "learn/scratch_exact.py", "learn/scratch_voice.py",
          "learn/voice_build.py", "learn/voice_floors.py", "learn/rederive_rows.py", "learn/scratch_loudar.py",
          "learn/scratch_codec.py", "learn/rederive_fit.py", "learn/scratch_rederive.py", "learn/note_transcribe.py",
          "learn/note_replay.py")   # the row's imports and amendment 11's pinned files
CODE_FILES = (MODULE,) + PINNED

ROW = "fs-own"
DRY = SV.OWN                             # "vc-own"
REF = SN.REF                             # "xlnoG": searched against xlnoG@-3, as fs-notes and fs-refit
COMPARATOR = SE.BUILD2                   # "b2": D_own = G(fs-own) - G(build 2)
STEM_ROW, BOTH_ROW = SE.STEM_ROW, SN.COMPARATOR   # rows (b) and (c)
LOUDAR = "ld-stem"                       # beside: LOUDAR's stored G50 (scratch_loudar)
LOUDAR_SETS = SL.DECIDING                # BKS and the panel (23 parts)
SEARCHED = ("true", SE.BANK_ARM, SV.AVG_MILD, RR.REAL_DRY)   # the no-carry check: guitars searched on these parts
MAX_SHARDS = RR.MAX_SHARDS               # 3
DECIDING = SE.DECIDING                   # BKS+GOAT, the 40; all 47 beside
SMALL, BIG = S.SMALL, S.BIG              # 0.05, 0.10: they label only (`paired_reading`)
ARMS = RR.ARMS                           # answer (decides), shrunk, cp50, cp100, cp200
DECIDING_ARM = RR.DECIDING_ARM
SHRUNK_SENSITIVE = "shrunk-sensitive"
NOT_COMPUTABLE = SV.NOT_COMPUTABLE

# Seen before the declaration (the reproduce check holds the first to 3 places; the rest are reported beside)
SEEN = {"b2_less_row_b": (0.274, 0.186, 0.361)}
SEEN_BESIDE = {"G_b2": (0.009, -0.088, 0.106), "G_row_b": (-0.264, -0.310, -0.219),
               "b2_less_row_b_cp50": (0.230, 0.147, 0.314), "b2_less_row_b_shrunk": (0.143, 0.075, 0.212),
               "vc_own_floor": (0.321, 0.261, 0.380), "loudar_less_b2_cp50_bp": (0.002, -0.116, 0.121)}

# --- the control's gate (amendments 3 and 4, as the control's review settled them) -----------------------------------

CONTROL_OUTCOME = SV.PHASE_CONTROL_OUTCOME    # phase_scratch_voice_control_outcome
XC_DECLARED = ("XC-anomaly", "XC-stands", "XC-part", "XC-notes", "XC-undecided")
XC_STOP = ("XC-anomaly",)                # the row stops (this module's own check, beside the spend gate's)
XC_WAIT = ("XC-notes",)                  # the row waits for the user's renewed word (the spend gate's waiver)
XC_WAIT_IF_COVERAGE = ("XC-part",)       # ... and so does XC-part marked coverage-sensitive
XC_PROCEED = ("XC-stands", "XC-part", "XC-undecided")   # on the user's 2026-11-28 go
COVERAGE_SENSITIVE = "coverage-sensitive"
COVERAGE_FIELD = "coverage_label"        # the control's outcome: "coverage-sensitive" or null
COVERAGE_LABELS = (None, COVERAGE_SENSITIVE)
COVERAGE_CODES = XC_WAIT_IF_COVERAGE + XC_WAIT   # the label must be there (fails closed, as spend_refusal since #658)
WAIVER = SV.PHASE_WAIVER                 # phase_scratch_voice_waiver: answers_code, date, spend_kinds ("search-row")
SPEND_KIND = "search-row"


def control_gate(entry):
    """(Pure.) How the row reads main's control outcome, as a second check beside the spend gate. -> (state, refusal
    or None): state "absent" or "stop" (refused), "wait" (the renewed word must be in the waiver; `require_spend`
    enforces it) or "proceed"."""
    ctl = (entry or {}).get(CONTROL_OUTCOME)
    code = ctl.get("code") if isinstance(ctl, dict) else None
    if not code:
        return "absent", f"main has no {CONTROL_OUTCOME} code: the control's audited outcome first; the row waits"
    if code not in XC_DECLARED:
        return "stop", f"the control's code {code!r} is not a declared XC code: the row stops; to the orchestrator"
    if code in XC_STOP:
        return "stop", f"{code}: the control's construction is off; the row stops; to the user"
    if code in COVERAGE_CODES and (COVERAGE_FIELD not in ctl or ctl[COVERAGE_FIELD] not in COVERAGE_LABELS):
        return "stop", (f"{code}: the control's outcome carries no {COVERAGE_FIELD} (None or {COVERAGE_SENSITIVE}): "
                        "the row stops (fails closed); to the orchestrator")
    if code in XC_WAIT or (code in XC_WAIT_IF_COVERAGE and ctl[COVERAGE_FIELD] == COVERAGE_SENSITIVE):
        return "wait", None
    return "proceed", None


def require_row_spend(m):
    """Refuse a render unless the control's code lets the row go on (`control_gate`: absent or XC-anomaly stops) and
    the sound gap's spend gate opens a search-row spend (`scratch_voice.require_spend("search-row")`: under XC-notes
    or a coverage-sensitive XC-part only with the user's renewed word in `phase_scratch_voice_waiver`, answering that
    code, dated on or after the control's outcome, `spend_kinds` holding "search-row"). -> main's entry."""
    state, why = control_gate(m)
    if why:
        raise SystemExit(why)
    mm = SV.require_spend(SPEND_KIND)
    state, why = control_gate(mm)
    if why:
        raise SystemExit(why)
    return mm


# --- the outcome table (pure) ----------------------------------------------------------------------------------------

DEFERRED = ("finer corrections of the bank's spectral envelope may follow, on their own declaration and table, after "
            "this row's code is on main")
XW_TABLE = (    # (code, when, said, decides); on the 40, the answer arm, the first that holds
    ("XW-anomaly", "a check fails, a stored figure does not reproduce, any of D_own, -D_own and C_own has no usable "
     "interval or reading, or C_own reads better",
     "unexpected; audit. If the audit finds no fault, the figures go to the user as read, never dropped",
     "stop; audit; nothing said before the audit"),
    ("XW-worse", "D_own reads worse",
     "if the audit finds no fault: real audio inside our note windows drives the search worse than the bank guitar",
     "audit the gate and the cuts first; routes 1 and 2 are not supported"),
    ("XW-closed", "D_own reads better and C_own reads matches",
     "the cost is recovered: a heard-size loss against the true DI is ruled out, by the score",
     "routes 1 and 2 stay open with the whole cost to gain; " + DEFERRED),
    ("XW-part", "D_own reads better and C_own does not read matches",
     "a heard-size part of the cost is recovered, by the score; C_own reads {c_reading}: a residual is shown "
     "(worse) or only not ruled out (undecided)",
     "routes 1 and 2 stay open; their room is at most -D_own; " + DEFERRED + "; the residual belongs to N, K and F "
     "together"),
    ("XW-level", "-D_own reads matches",
     "a heard-size gain from real audio inside our note windows is ruled out, by the score",
     "routes 1 and 2 cannot pay by search; C_own's residual holds N, K and F together (F, +0.172 at the floor, is "
     "larger than N there): the cheap split of C_own is the 50-evaluation vc-fin row (about 2.6k renders), on its own "
     "declaration and go; the deferred envelope corrections do not run"),
    ("XW-undecided", "anything else", "not decided; undecided is not failed{c_note}",
     "to the user with what the intervals rule out (D_own {d_lo} to {d_hi})"),
)
XW_CODES = tuple(c for c, *_ in XW_TABLE)
XW_DECLARED = ("XW-anomaly", "XW-worse", "XW-closed", "XW-part", "XW-level", "XW-undecided")
CHECKS = ("checks_passed", "reproduces")


def iv_ok(iv):
    return SV.iv_ok(iv)


def reading(iv):
    """(Pure.) `scratch_notes.paired_reading` of a usable interval, else None."""
    return SV.reading(iv)


def _r(iv):
    return (reading(iv) or {}).get("reading")


def neg(iv):
    """(Pure.) The interval of -x: build 2 against the row. None unless usable."""
    if not iv_ok(iv):
        return None
    return {"mean": -float(iv["mean"]), "lo90": -float(iv["hi90"]), "hi90": -float(iv["lo90"])}


def table_guard():
    """Refuse unless XW_TABLE holds its declared codes in order, its last row is literally "anything else", 0 < SMALL
    < BIG, the key prefix sits outside every guarded prefix and the control's codes split into stop, wait and
    proceed."""
    if XW_CODES != XW_DECLARED:
        raise SystemExit("XW_TABLE's codes are not the six declared, in order")
    if XW_TABLE[-1][1] != "anything else":
        raise SystemExit("XW_TABLE's last row is not 'anything else'")
    if not 0 < SMALL < BIG:
        raise SystemExit("the thresholds are not 0 < SMALL < BIG")
    if not KEY_PREFIX.startswith("phase_scratch_") or KEY_PREFIX.startswith(GUARDED_PREFIXES):
        raise SystemExit(f"{KEY_PREFIX} sits under a guarded prefix")
    parts = (set(XC_STOP), set(XC_WAIT), set(XC_PROCEED))
    if (set().union(*parts) != set(XC_DECLARED) or sum(map(len, parts)) != len(XC_DECLARED)
            or not set(XC_WAIT_IF_COVERAGE) <= set(XC_PROCEED)):
        raise SystemExit("the control's codes do not split into stop, wait and proceed")
    if (XC_DECLARED != SV.CONTROL_CODES or XC_STOP != SV.CONTROL_SHUT or XC_WAIT != SV.CONTROL_WAIVER_ONLY
            or set(COVERAGE_CODES) != set(SV.COVERAGE_FORCED) or COVERAGE_SENSITIVE != SV.COVERAGE_SENSITIVE):
        raise SystemExit("the row's control gate does not read the codes as scratch_voice's spend gate declares them")


def anomaly_why(d_own, c_own, checks):
    """(Pure.) Why XW-anomaly holds, or None (amendment 1: a missing or malformed interval is an anomaly)."""
    for c in CHECKS:
        if (checks or {}).get(c) is not True:
            return f"the check {c} does not hold"
    for name, iv in (("D_own", d_own), ("-D_own", neg(d_own)), ("C_own", c_own)):
        if reading(iv) is None:
            return f"{name} has no usable interval or reading"
    if _r(c_own) == "better":
        return "C_own reads better"
    return None


def _fmt(x):
    return f"{x:+.3f}" if isinstance(x, (int, float)) and math.isfinite(x) else "n/a"


def xw_code(d_own, c_own, checks):
    """(Pure.) XW_TABLE's one code, the first that holds: `paired_reading` of D_own, -D_own and C_own on the 40.
    checks: {checks_passed, reproduces: bool}. -> dict."""
    why = anomaly_why(d_own, c_own, checks)
    rd, rn, rc = _r(d_own), _r(neg(d_own)), _r(c_own)
    if why:
        code = "XW-anomaly"
    elif rd == "worse":
        code = "XW-worse"
    elif rd == "better" and rc == "matches":
        code = "XW-closed"
    elif rd == "better":
        code = "XW-part"
    elif rn == "matches":
        code = "XW-level"
    else:
        code = "XW-undecided"                              # anything else
    row = next(r for r in XW_TABLE if r[0] == code)
    c_note = ("; C_own reads matches: a heard-size loss against the true DI is ruled out"
              if code == "XW-undecided" and rc == "matches" else "")
    d = d_own if iv_ok(d_own) else {}
    return {"code": code, "when": row[1], "said": row[2].format(c_reading=rc, c_note=c_note),
            "decides": row[3].format(d_lo=_fmt(d.get("lo90")), d_hi=_fmt(d.get("hi90"))), "anomaly": why,
            "readings": {"D_own": reading(d_own), "minus_D_own": reading(neg(d_own)), "C_own": reading(c_own)}}


def arm_codes(ivs, checks):
    """(Pure.) Each arm's code beside ({arm: (D_own, C_own)}) and `shrunk-sensitive` when the shrunk arm's code is not
    the answer arm's. -> {codes, label}."""
    codes = {a: xw_code(d, c, checks)["code"] for a, (d, c) in ivs.items()}
    lab = SHRUNK_SENSITIVE if codes.get("shrunk") != codes.get(DECIDING_ARM) else None
    return {"codes": codes, "label": lab}


# --- the guards (pure parts) -----------------------------------------------------------------------------------------

def shard_refusal(shard):
    return RR.shard_refusal(shard)


def own_keys(entry):
    """(Pure.) This row's own keys of a `preset-ladder` entry."""
    return {k: v for k, v in (entry or {}).items() if k.startswith(KEY_PREFIX)}


def keys_refusal(local, main):
    """(Pure.) Why this checkout's `phase_scratch_own*` keys are not main's, or None."""
    a, b = own_keys(local), own_keys(main)
    if a != b:
        return f"this checkout's {sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))} differ from main's"
    return None


def carry_hit(sha, searched):
    """(Pure.) The searched guitar `vc-own` is byte-identical to, or None. searched: {name: sha256 or None}."""
    for name in SEARCHED:
        if sha and searched.get(name) == sha:
            return name
    return None


# The search's forbidden files (amendment 6): rederive_rows' (and scratch_exact's), and these
FORBIDDEN_NAMES = ("answers.json", "rows.json", "report.json", "reproduce.json", "outcome.json")
FORBIDDEN_PREFIXES = ("answers-", "rows-", "report-", "read-", "floors-real-")
FORBIDDEN_DIRS = ("score", "floors", "floors-real", "floors-first", "repeat", "floor-repeat")   # and their -rerun/
FORBIDDEN_TREES = (("voice", "control"), ("fs", "envelope"))   # anything under PF/fs/voice/control/, PF/fs/envelope/


def is_forbidden(path):
    """(Pure.) Whether the search may not open `path`: `rederive_rows.is_forbidden` (scratch_exact's too), any
    answers, rows, report, reproduce or outcome file, anything under a score, floor or repeat folder (the voice test's
    and the control's included), under PF/fs/voice/control/ or PF/fs/envelope/."""
    path = pathlib.PurePath(path)
    if RR.is_forbidden(path):
        return True
    name = path.name
    if name in FORBIDDEN_NAMES or name.startswith(FORBIDDEN_PREFIXES):
        return True
    for part in path.parent.parts:
        base = part[:-len("-rerun")] if part.endswith("-rerun") else part
        if base in FORBIDDEN_DIRS:
            return True
    parts = path.parts
    return any(tuple(parts[i:i + 2]) == t for i in range(len(parts) - 1) for t in FORBIDDEN_TREES)


def search_open(path):
    """Every file the search reads of its own goes through here: a forbidden one refuses."""
    if is_forbidden(path):
        raise SystemExit(f"{pathlib.PurePath(path).name}: the search never opens it")
    return pathlib.Path(path)


def tag(pk):
    return SV.tag(pk)


# --- paths ------------------------------------------------------------------------------------------------------------

def own_dir():
    return S.fs_dir() / "own"


def check_dir(kind):
    if kind not in ("check-score", "check-search"):
        raise ValueError(kind)
    return own_dir() / "checks" / kind


def search_path(pk):
    return own_dir() / "search" / f"{SE._f(pk)}.json"


def start_path(pk):
    return own_dir() / "start-ref" / f"{SE._f(pk)}.json"


def answers_path():
    """The row's answers (PF/fs/own/answers.json); its sha256 is main's phase_scratch_own_answers before the score."""
    return own_dir() / "answers.json"


def score_path(pk):
    return own_dir() / "score" / f"{SE._f(pk)}.json"


def rows_path():
    return own_dir() / "rows.json"


def report_path():
    return own_dir() / "report.json"


def reproduce_path():
    return own_dir() / "reproduce.json"


def control_rows_path():
    """The control's rows.json (`voice_control`: PF/fs/voice/control/rows.json, per part by 12-hex tag); the read
    takes Ux from it beside, hash-checked against main's control outcome `rows_sha256`."""
    return SV.voice_dir() / "control" / "rows.json"


# --- the guards -------------------------------------------------------------------------------------------------------

BASE = (S.PHASE, S.PHASE_DRAW, SV.PHASE_DRY, PHASE)
REPRO_PHASES = (S.phase_answers(STEM_ROW), SE.PHASE_B2_ANSWERS, SE.PHASE_OUTCOME, SL.phase_answers(LOUDAR),
                SL.PHASE_OUTCOME, SV.PHASE_OUTCOME)
PHASES = {"check-score": (S.phase_answers(BOTH_ROW),), "check-search": (), "search": (SE.PHASE_BANK, RD.PHASE_FROZEN),
          "answers": (), "score": (PHASE_ANSWERS,), "reproduce": REPRO_PHASES,
          "read": REPRO_PHASES + (PHASE_ANSWERS, S.phase_answers(BOTH_ROW), SE.PHASE_TARGETS, CONTROL_OUTCOME)}
RENDER_COMMANDS = ("check-score", "check-search", "search", "score")


def pinned_identity():
    """Each of CODE_FILES equal to origin/main's (git diff --quiet). -> {file: same}."""
    return {f: SE._git("diff", "--quiet", "origin/main", "--", f).returncode == 0 for f in CODE_FILES}


def require_own(*phases):
    """Refuse unless the table holds, this checkout runs main's search (`scratch_search.require_on_main`), this module
    and the pinned files are main's, the `phase_scratch_own*` and `phase_scratch_voice*` keys are main's, and main holds
    the draw, the voice build's hash, this declaration and `phases`. -> main's `preset-ladder` entry."""
    from learn import note_replay as NRP

    table_guard()
    m = S.require_on_main(*BASE, *phases)
    bad = [f for f, ok in pinned_identity().items() if not ok]
    if bad:
        raise SystemExit(f"this checkout's {bad} differ from main's: run from merged code")
    local = NRP.ledger_entry()
    why = keys_refusal(local, m) or SV.keys_refusal(local, m)
    if why:
        raise SystemExit(why)
    return m


def voice_build(m):
    """The sound gap's build.json, refused unless its sha256 is main's phase_scratch_voice_dry and its proofs held."""
    p = search_open(SV.build_path())
    if not p.exists():
        raise SystemExit("no voice build.json (voice_build's build first)")
    b = NT.require_file_hash(m, SV.PHASE_DRY, p)
    if b.get("proofs_hold") is not True:
        raise SystemExit("the voice build's proofs did not hold")
    return b


def guitar_entry(pk, vb):
    return (((vb or {}).get("parts") or {}).get(pk) or {}).get("guitars", {}).get(DRY) or {}


def guitar_sha(pk, vb):
    """The declared sha256 (of the float32 .npy bytes) of a part's vc-own: build.json's `audio_sha256`."""
    return guitar_entry(pk, vb).get("audio_sha256")


def load_guitar(pk, vb):
    """A part's stored vc-own, float32, refused unless its file is build.json's `file_sha256` and its samples its
    `audio_sha256`."""
    import numpy as np

    e = guitar_entry(pk, vb)
    path = search_open(SV.dry_path(DRY, pk))
    if not e.get("file_sha256") or not path.exists() or S.file_sha(path) != e["file_sha256"]:
        raise SystemExit(f"part {tag(pk)}: vc-own's file is not the one build.json declares")
    x32 = np.load(path).astype(np.float32)
    if not e.get("audio_sha256") or S.npy_sha(x32) != e["audio_sha256"]:
        raise SystemExit(f"part {tag(pk)}: vc-own's samples are not build.json's audio_sha256")
    return x32


def searched_world(m):
    """The records the no-carry check reads: build 2 (tr-di) and fs-refit's build-real (rf2), each hash-checked."""
    return {"b2": SE.bank_build(m), "rf2": RR.fit_build(m, "real")}


def searched_shas(p, w, vb, sd):
    """Per part the sha256 of each searched guitar (SEARCHED) on it."""
    from learn import note_replay as R

    pk = p["pkey"]
    prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
    return {"true": S.npy_sha(R.di_section(prt)),
            SE.BANK_ARM: (((w["b2"]["parts"].get(pk) or {}).get("arms") or {}).get(SE.BANK_ARM) or {}).get("sha256"),
            SV.AVG_MILD: ((vb["parts"][pk].get("guitars") or {}).get(SV.AVG_MILD) or {}).get("audio_sha256"),
            RR.REAL_DRY: (w["rf2"]["parts"].get(pk) or {}).get("audio_sha256")}


def check_results():
    res = {}
    for kind in ("check-score", "check-search"):
        p = check_dir(kind) / "result.json"
        res[kind] = json.loads(p.read_text()) if p.exists() else None
    return res


def require_checks():
    """Both of the row's checks ran and passed (`scratch_notes.checks_passed`). -> {kind: result}."""
    res = check_results()
    why = SN.checks_passed(res["check-score"], res["check-search"])
    if why:
        raise SystemExit(f"{ROW}'s {why}")
    return res


def _guard_shard(args):
    why = shard_refusal(getattr(args, "shard", (0, 1)))
    if why:
        raise SystemExit(why)


# --- the checks (renders, once) ---------------------------------------------------------------------------------------

def cmd_check_score(_args):
    """Row (c)'s first BKS and first GOAT part re-scored through `scratch_search.score_row_part`, as this row scores
    (`rederive_rows check-score --for real`): every held value and render sha256 must equal row (c)'s stored score
    file (`scratch_notes.score_check_verdict`). Written once. -> checks/check-score/."""
    m = require_own(*PHASES["check-score"])
    require_row_spend(m)
    d = check_dir("check-score")
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
        rec, used = S.score_row_part(by[k], ans["parts"][k], ans["parts"], BOTH_ROW,
                                     S.file_sha(S.answers_path(BOTH_ROW)), sd, CB.new_renderer)
        total += used
        P.save(out, rec)
        new[k], stored[k] = rec, json.loads(S.score_path(BOTH_ROW, k).read_text())
    verdict = SN.score_check_verdict(new, stored)
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    res = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "renders": total, "passed": verdict["passed"],
           "mismatches": check_mismatches(verdict["mismatches"], sets_of), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(d / "result.json", res)
    print(f"FS-OWN CHECK-SCORE {'PASS' if res['passed'] else 'FAIL'}: {total} renders; mismatches {res['mismatches']}")


def cmd_check_search(_args):
    """On the same two parts: `scratch_search.run_part` with row (c)'s inputs (avg+mild, `xlnoG@-3` blanked, row (c)'s
    start reference passed explicitly) and a step-1 budget of CHECK_BUDGET, stopped after step 1, as `rederive_rows
    check-search --for real`: the evaluations must equal the start of row (c)'s stored curve exactly. Written once.
    -> checks/check-search/."""
    m = require_own(*PHASES["check-search"])
    require_row_spend(m)
    d = check_dir("check-search")
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
        x32 = R.load_dry(SV.AVG_MILD, rby[k], R.di_section(prt), blur)
        sha = blur["parts"][k]["sha256"][SV.AVG_MILD]
        ref_blank = S.load_ref_blank(sd, p, REF)
        rec = S.run_part(p, SV.AVG_MILD, REF, x32, ref_blank, CB.new_renderer, lists, budget=SN.CHECK_BUDGET,
                         start_ref=p["start_ref"][SV.AVG_MILD][REF], dry_sha256=sha, step1_only=True)
        total += rec.get("renders", 0)
        P.save(out, rec)
        new[k], stored[k] = rec, json.loads(S.search_path(BOTH_ROW, k).read_text())
    verdict = SN.search_check_verdict(new, stored)
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    res = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "renders": total, "budget": SN.CHECK_BUDGET,
           "passed": verdict["passed"], "mismatches": check_mismatches(verdict["mismatches"], sets_of),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(d / "result.json", res)
    print(f"FS-OWN CHECK-SEARCH {'PASS' if res['passed'] else 'FAIL'}: {total} renders; mismatches "
          f"{res['mismatches']}")


# --- the row: search, answers, score ----------------------------------------------------------------------------------

def cmd_search(args):
    """One shard of the row's searches (renders), as `rederive_rows._search_real` with this row's guitar, keys and
    folders and no carry: per part (sorted by key, every n-th) the stored vc-own (its file and samples build.json's),
    refused if byte-identical to a searched guitar (`carry_hit`); `scratch_notes.start_reference`, then
    `scratch_search.search_row_part` against `xlnoG@-3` blanked outside the search half, with `dry_sha256`. `--rerun`:
    a refused record once more in this fresh process (S1). The disk guard before every part; nothing scored opened."""
    _guard_shard(args)
    m = require_own(*PHASES["search"])
    require_row_spend(m)
    require_checks()
    vb = voice_build(m)
    w = searched_world(m)
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import local_objective as LO
    from learn import note_replay as R

    R.no_separation_beside()
    draw, sd = SE.context()
    todo = SE.mine(draw, args.shard)
    lists = C.mic_lists()
    LO._wait_cap()
    rerun = getattr(args, "rerun", False)
    total, t0 = 0, time.time()
    for p in todo:
        pk = p["pkey"]
        out = search_path(pk)
        if rerun:                                        # S1: a technical refusal, once more in this fresh process
            if not out.exists() or not S.refused_record(json.loads(out.read_text())):
                continue
            out = S.rerun_path(out)
        if out.exists():
            continue
        SE.disk_guard()
        sha = guitar_sha(pk, vb)
        x32 = load_guitar(pk, vb)
        hit = carry_hit(sha, searched_shas(p, w, vb, sd))
        if hit:
            raise SystemExit(f"part {tag(pk)}: vc-own is {hit}'s audio byte for byte: no carry; the row stops, to the "
                             "orchestrator")
        ref_blank = S.load_ref_blank(sd, p, REF)
        spath = start_path(pk)
        if rerun:
            spath = S.rerun_path(spath)
        sref, used = SN.start_reference(p, x32, ref_blank, CB.new_renderer, spath, sha)
        rec = S.search_row_part(p, DRY, REF, x32, ref_blank, CB.new_renderer, lists, out, f"{LEDGER_ID} {PHASE}",
                                start_ref=sref, dry_sha256=sha)
        total += rec.get("renders", 0) + used
        if "refused" in rec:
            print(f"part {tag(pk)}: REFUSED {rec['refused']}", flush=True)
        print(f"{ROW} shard {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s "
              f"({total / max(1, time.time() - t0) * 3600:.0f} an hour)", flush=True)
    print(f"FS-OWN SEARCH DONE {args.shard[0]}/{args.shard[1]}{' (rerun)' if rerun else ''}: {total} renders in "
          f"{time.time() - t0:.0f} s")


def cmd_answers(_args):
    """The row's answers (zero renders), as `rederive_rows cmd_answers` for fs-refit: every search record or its
    passing rerun (`with_reruns`; one not yet rerun waits, `rerun_refusal`), each dry guitar build.json's
    (`scratch_exact.dry_refusal`) and named vc-own (no carry); `answer_parts` (the borrowed answers and the centre) and
    `deciding_stop`; the refusals reported (S1). -> answers.json; its sha256 into the ledger as
    phase_scratch_own_answers before `score`."""
    m = require_own(*PHASES["answers"])
    state, why = control_gate(m)
    if why:
        raise SystemExit(why)
    NT.never_overwrite(answers_path())
    from learn import pipeline_fix as P

    draw, _sd = SE.context()
    keys = [p["pkey"] for p in draw["parts"]]
    for k in keys:
        if not search_path(k).exists():
            raise SystemExit(f"part {tag(k)}: not searched")
    recs, used, reruns = S.with_reruns(keys, search_path)
    why = S.rerun_refusal(reruns)
    if why:
        raise SystemExit(why)
    vb = voice_build(m)
    checks = require_checks()
    why = SE.dry_refusal(recs, {k: guitar_sha(k, vb) for k in keys})
    if why:
        raise SystemExit(why)
    other = sorted(tag(k) for k, r in recs.items() if "refused" not in r and r.get("dry") != DRY)
    if other:
        raise SystemExit(f"{len(other)} record(s) are not vc-own's search ({other}): no carry; to the orchestrator")
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    out = {"plan": PLAN, "row": ROW, "draw_sha256": S.file_sha(S.draw_path()),
           "time": time.strftime("%Y-%m-%d %H:%M:%S"),
           "renders": sum(r.get("renders", 0) for r in recs.values()), "reruns": reruns,
           "checks_sha256": {kind: S.file_sha(check_dir(kind) / "result.json") for kind in checks}, "stopped": False}
    parts, refused = S.answer_parts(draw, recs, lambda k: S.file_sha(used[k]))
    dec, pan, _stop = SN.deciding_stop(refused, sets_of)
    out.update(dry=DRY, ref=S.REF_NAME[REF], build_sha256=S.file_sha(SV.build_path()), refused_deciding=dec,
               refused_panel=pan)
    out.update(refused=refused, refusal_report=S.refusal_report(refused, sets_of, DECIDING), parts=parts)
    P.save(answers_path(), out)
    print(f"FS-OWN ANSWERS: {len(parts)} parts, {len(refused)} refused (each reads at Cen); reruns "
          f"{ {tag(k): v for k, v in reruns.items()} }; sha256 {S.file_sha(answers_path())} (into the ledger as "
          f"{PHASE_ANSWERS} before `score`)")


def cmd_score(args):
    """One shard of the row's score (renders), from its hashed answers, as `rederive_rows cmd_score` for fs-refit:
    `scratch_search.score_row_part` (Cen, the answer, cp50, cp100, cp200, the shrunk answer and the borrowed answers
    through the true DI, against the clean record), the scoring control against Cen's stored value; `--rerun`: a
    control miss once more in this fresh process (S1). -> score/<part>.json."""
    _guard_shard(args)
    m = require_own(*PHASES["score"])
    require_row_spend(m)
    ans = NT.require_file_hash(m, PHASE_ANSWERS, answers_path())
    asha = S.file_sha(answers_path())
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
        out = score_path(pk)
        a = ans["parts"].get(pk)
        if getattr(args, "rerun", False):                # S1: a scoring-control miss, once more in this fresh process
            if a is None or not out.exists() or json.loads(out.read_text())["scoring_control_ok"]:
                continue
            out = S.rerun_path(out)
        if a is None or out.exists():
            continue
        SE.disk_guard()
        rec, used = S.score_row_part(p, a, ans["parts"], ROW, asha, sd, CB.new_renderer)
        total += used
        P.save(out, rec)
        print(f"part {tag(pk)}: scored {rec['distinct_renders']} settings; control "
              f"{'ok' if rec['scoring_control_ok'] else 'MISS'}; {total} renders, {time.time() - t0:.0f} s", flush=True)
    print(f"FS-OWN SCORE DONE {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s")


# --- the read (zero renders) ------------------------------------------------------------------------------------------

def own_numbers(m, draw, sd):
    """The row's per-part numbers through `scratch_search.read_row_parts` from its hashed answers and score files (as
    `rederive_rows.real_numbers` reads fs-refit). -> {per, itt (S1), refused, replaced, control_misses,
    answers_sha256}."""
    from learn import note_replay as R

    ans = NT.require_file_hash(m, PHASE_ANSWERS, answers_path())
    if ans.get("dry") != DRY or ans.get("build_sha256") != (m.get(SV.PHASE_DRY) or {}).get("sha256"):
        raise SystemExit("answers.json is not vc-own's from main's voice build")
    sha = S.file_sha(answers_path())
    rby = {p["pkey"]: p for p in R.require_draw()["parts"]}
    per, refused, replaced, ctl = S.read_row_parts(draw, ans, sha, score_path, sd, rby)
    return {"per": per, "itt": S.itt_per(per, refused, S.G_FIELDS), "refused": refused, "replaced": replaced,
            "control_misses": ctl, "answers_sha256": sha}


def _iv(r):
    return {q: (r or {}).get(q) for q in ("mean", "lo90", "hi90")} if r else None


def the_40(sd, draw, vals, keys=None):
    return RR.the_40(sd, draw, vals, keys)


def close3(iv, seen):
    return iv_ok(iv) and all(round(float(iv[q]), 3) == v for q, v in zip(("mean", "lo90", "hi90"), seen))


def groups_of(draw, tg):
    """The beside splits' part sets: the 40 (deciding), its clusters, one part per partner (the exact-notes targets'
    partners)."""
    deciding = sorted(p["pkey"] for p in draw["parts"] if p["set"] in DECIDING)
    clusters = {}
    for p in draw["parts"]:
        if p["set"] in DECIDING:
            clusters.setdefault(p["cluster"], []).append(p["pkey"])
    return {"deciding": deciding, "clusters": [sorted(v) for _, v in sorted(clusters.items())],
            "one_per_partner": SE.one_per_partner({k: t["partner"] for k, t in tg["parts"].items()})}


def splits(sd, draw, vals, groups, full=True):
    """One paired figure on the declared splits: the 40 (deciding), clean and crunch, all 47 and the panel; with `full`
    each cluster of the 40 left out, the three largest parts (their tags, contribution and the 40 without them) and
    one part per partner."""
    r = SN.set_rows(sd, draw, vals)
    bg = (r or {}).get("bks_goat") or {}
    out = {"the_40": bg.get("all"), "clean": bg.get("clean"), "crunch": bg.get("crunch"),
           "all_47": (r or {}).get("deciding_pool"), "panel": _iv((r or {}).get("panel")),
           "per_set": {s: _iv((r or {}).get(s)) for s in S.SETS} if r else None,
           "parts": len([v for v in vals.values() if v is not None])}
    if not full:
        return out
    dec = groups["deciding"]
    out["cluster_left_out"] = [the_40(sd, draw, vals, set(dec) - set(c)) for c in groups["clusters"]]
    means = [x["mean"] for x in out["cluster_left_out"] if iv_ok(x)]
    out["cluster_left_out_range"] = [min(means), max(means)] if means else None
    top = SV.largest(vals, dec)
    out["largest_three"] = {"tags": [tag(k) for k in top], "values": [vals[k] for k in top],
                            "contribution": the_40(sd, draw, RR.contributions(vals, set(top))),
                            "without": the_40(sd, draw, vals, set(dec) - set(top))}
    keep = set(groups["one_per_partner"])
    n_all, n_40 = len(keep & set(vals)), len(keep & set(vals) & set(dec))
    out["one_per_partner"] = {"parts_all_47": n_all, "parts_on_the_40": n_40, "iv": the_40(sd, draw, vals, keep)}
    return out


def figure(sd, draw, new, old, groups):
    """A paired figure G(new) - G(old) on every arm (the answer on every split; the shrunk arm and the checkpoints on
    the 40, clean, crunch, all 47 and the panel), each arm's `paired_reading` on the 40."""
    out = {}
    for arm, f in ARMS.items():
        s = splits(sd, draw, SN.paired_values(new, old, f), groups, full=(arm == DECIDING_ARM))
        s["reading"] = SN.paired_reading(s["the_40"])
        out[arm] = s
    return out


def loudar_g50(m, draw):
    """ld-stem's per-part G50 from its hashed answers and score files (`scratch_loudar.g50_of`), S1 as LOUDAR's read:
    a refused part at Cen. -> (itt {pkey: value}, passing {pkey: value}, refused)."""
    per, refused, _rep, _miss = SL.g50_of(draw, LOUDAR, m)
    itt = {k: v for k, v in S.itt_values(per, refused).items() if v is not None}
    return itt, {k: v for k, v in per.items() if v is not None}, refused


def loudar_rows(sd, draw, own, ld, sets_of):
    """(Pure but for `bp_rows`.) G at cp50 of fs-own less ld-stem's G50 on BKS+panel, pooled as
    `scratch_loudar.bp_rows`, the part-weighted mean beside, read both ways. own: {pkey: G_cp50}; ld: {pkey: G50}."""
    d = {k: own[k] - ld[k] for k in own if k in ld and sets_of.get(k) in LOUDAR_SETS}
    rows = SL.bp_rows(sd, draw, d) if d else None
    bp = (rows or {}).get("bp")
    r, rn = _r(bp), _r(neg(bp))
    return {"bp": _iv(bp), "bks": _iv((rows or {}).get("bks")), "panel": _iv((rows or {}).get("panel")),
            "parts": len(d), "part_weighted_mean": statistics.mean(d.values()) if d else None,
            "reading": r, "minus_reading": rn,
            "said": ("the oracle ceiling sits above the released song-only rebuild on unseen sets, by the score"
                     if r == "better" else "the oracle ceiling is not shown to sit above the released song-only "
                     "rebuild on unseen sets"), "label": "beside; never changes the code"}


def rank_beside(neg_d, by_tag, deciding):
    """(Pure.) Spearman of a stored per-part figure (by 12-hex tag) against -D_own on the 40, or NOT_COMPUTABLE."""
    if not isinstance(by_tag, dict):
        return {"rho": NOT_COMPUTABLE, "parts": 0}
    ks = [k for k in deciding if neg_d.get(k) is not None and isinstance(by_tag.get(tag(k)), (int, float))]
    rho = SV.spearman([by_tag[tag(k)] for k in ks], [neg_d[k] for k in ks])
    return {"rho": NOT_COMPUTABLE if rho is None else rho, "parts": len(ks)}


def _hashed_rows(m, path, phase, field):
    """A stored rows.json's per_part, refused (None, reason) unless its sha256 is main's `phase` `field`."""
    p = pathlib.Path(path)
    if not p.exists():
        return None, f"no {p.name} at {phase}'s place"
    want = (m.get(phase) or {}).get(field) if isinstance(m.get(phase), dict) else None
    if not want or want != S.file_sha(p):
        return None, f"{p.name}'s sha256 is not main's {phase} {field}"
    return (json.loads(p.read_text()).get("rows") or {}).get("per_part"), None


def reproduce(m, draw, sd):
    """Zero renders: build 2 less row (b) on the 40 through this module's read (`rederive_rows.real_numbers`,
    `the_40`), equal to the exact-notes read's stored row exactly (its rows.json main's `phase_scratch_exact_outcome`
    rows_sha256) and to the declared figure to 3 places; LOUDAR's G50 on BKS+panel through `scratch_loudar.bp_rows`
    equal to LOUDAR's stored row exactly (its rows.json main's `phase_scratch_loudar_outcome`). The seen figures beside
    (reported to 3 places, gating nothing). -> {figures, stored, exact, seen, seen_beside, holds}."""
    rb, rn = RR.real_numbers(m, draw, sd, STEM_ROW), RR.real_numbers(m, draw, sd, COMPARATOR)
    got = {"b2_less_row_b": the_40(sd, draw, SN.paired_values(rn["itt"], rb["itt"], "G"))}
    p = SE.rows_path()
    why = SE.field_refusal(m, SE.PHASE_OUTCOME, "rows_sha256", S.file_sha(p))
    if why:
        raise SystemExit(why)
    want = {"b2_less_row_b": json.loads(p.read_text())["rows"]["beside"]["answer"]["real_gap"]["bks_goat"]["all"]}
    lp = SL.rows_path()
    lw = ((m.get(SL.PHASE_OUTCOME) or {}).get("read_files_sha256") or {}).get("rows.json")
    if not lw or lw != S.file_sha(lp):
        raise SystemExit(f"LOUDAR's rows.json is not main's {SL.PHASE_OUTCOME} read_files_sha256")
    ld_itt, _ld_pass, _ld_ref = loudar_g50(m, draw)
    got["loudar_g50_bp"] = (SL.bp_rows(sd, draw, ld_itt) or {}).get("bp")
    want["loudar_g50_bp"] = json.loads(lp.read_text())["rows"]["G50"]["bp"]
    exact = {n: iv_ok(got[n]) and iv_ok(want[n]) and all(got[n][q] == want[n][q] for q in ("mean", "lo90", "hi90"))
             for n in got}
    seen = {n: close3(got[n], v) for n, v in SEEN.items()}
    sets_of = {q["pkey"]: q["set"] for q in draw["parts"]}
    b2cp = {k: v["G_cp50"] for k, v in rn["itt"].items() if v and v.get("G_cp50") is not None}
    beside = {"G_b2": RR.own_g(sd, draw, rn["itt"])["iv"], "G_row_b": RR.own_g(sd, draw, rb["itt"])["iv"],
              "b2_less_row_b_cp50": the_40(sd, draw, SN.paired_values(rn["itt"], rb["itt"], "G_cp50")),
              "b2_less_row_b_shrunk": the_40(sd, draw, SN.paired_values(rn["itt"], rb["itt"], "G_shrunk")),
              "loudar_less_b2_cp50_bp": loudar_rows(sd, draw, ld_itt, b2cp, sets_of)["bp"]}
    vr, vwhy = _hashed_rows(m, SV.rows_path(), SV.PHASE_OUTCOME, "rows_sha256")
    if vr:
        by_key = {tag(k): k for k in sets_of}
        floor = {by_key[t]: vr["N"][t] + vr["K"][t] + vr["F"][t] for t in vr.get("N", {})
                 if t in by_key and None not in (vr["N"][t], vr["K"].get(t), vr["F"].get(t))}
        beside["vc_own_floor"] = the_40(sd, draw, floor)
    else:
        beside["vc_own_floor"] = None
    seen_beside = {n: {"iv": beside.get(n), "seen": v, "to_3_places": close3(beside.get(n), v)}
                   for n, v in SEEN_BESIDE.items()}
    return {"figures": got, "stored": want, "exact": exact, "seen": seen, "seen_beside": seen_beside,
            "voice_rows": vwhy or "read", "holds": all(exact.values()) and all(seen.values())}


SETTING_NAMES = ("cen", "answer", "cp50", "cp100", "cp200", "shrunk", "centre")   # score_row_part's own names
CHECK_WORDS = ("settings", "refused", "curve", "first render")   # the check verdicts' own words


def setting_tag(name, sets_of, plain=SETTING_NAMES):
    """(Pure.) A scored setting's public name: `plain`'s names (score_row_part's own) as they are; any other (a
    borrowed answer is named by its partner's part key) as the part's 12-hex tag."""
    return name if name in plain and name not in sets_of else tag(name)


def check_mismatches(mismatches, sets_of):
    """(Pure.) A check verdict's mismatches [(part, name)] for its result file: the part as its tag, the name by
    `setting_tag` (the verdicts' own words kept)."""
    return [[tag(k), setting_tag(nm, sets_of, SETTING_NAMES + CHECK_WORDS)] for k, nm in mismatches]


def _tagged_refusals(nums, sets_of):
    """(Pure but for `refusal_report`.) The rows' refusals with every part key as its 12-hex tag: the refused and
    missed parts, and the parts and setting names `nonfinite_rule` replaced (a partner's answer is named by its
    part key)."""
    out = {}
    for r, n in nums.items():
        ref = {tag(k): v for k, v in n["refused"].items()}
        out[r] = {"refused": ref, "report": S.refusal_report(ref, {tag(k): s for k, s in sets_of.items()}, DECIDING),
                  "control_misses": sorted(tag(k) for k in n["control_misses"]),
                  "nonfinite_replaced": {tag(k): [setting_tag(x, sets_of) for x in v]
                                         for k, v in n["replaced"].items()}}
    return out


def read_codes(D, pD, checks):
    """(Pure.) XW_TABLE's code on the answer arm with S1 (`rederive_rows.with_passing`: the passing-only code beside,
    `refusal-sensitive` when they differ), and every arm's code beside (`shrunk-sensitive`). D: {name: figure};
    pD: {D_own, C_own} passing-only intervals, or None. -> (code, passing code, refusal label, arms)."""
    def fn(d, c):
        return xw_code(d, c, checks)
    a = {n: v[DECIDING_ARM]["the_40"] for n, v in D.items()}
    code, cp, label = RR.with_passing(fn, (a["D_own"], a["C_own"]), (pD["D_own"], pD["C_own"]) if pD else None)
    arms = arm_codes({arm: (D["D_own"][arm]["the_40"], D["C_own"][arm]["the_40"]) for arm in ARMS}, checks)
    return code, cp, label, arms


def cmd_read(_args):
    """The read (zero renders), once: the stored figures reproduced first (`reproduce`); per part (S1) G(fs-own), build
    2, row (b) and row (c) from their hashed answers and score files; D_own, C_own and G(fs-own) - G(row (c)) on every
    arm and split; the rows saved before XW_TABLE's code; S1, the arms' codes, LOUDAR, Fieller's share and the ranks
    beside. Part keys appear only as 12-hex tags. -> rows.json, report.json."""
    m = require_own(*PHASES["read"])
    state, why = control_gate(m)
    if why:
        raise SystemExit(why)
    for p_ in (rows_path(), report_path()):
        NT.never_overwrite(p_)
    from learn import pipeline_fix as P

    draw, sd = SE.context()
    repro = reproduce(m, draw, sd)
    tg = SE.require_targets(m)
    groups = groups_of(draw, tg)
    checks_res = check_results()
    checks = {"checks_passed": SN.checks_passed(checks_res["check-score"], checks_res["check-search"]) is None,
              "reproduces": repro["holds"]}
    nums = {ROW: own_numbers(m, draw, sd), **{r: RR.real_numbers(m, draw, sd, r)
                                              for r in (COMPARATOR, STEM_ROW, BOTH_ROW)}}
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    it = {r: n["itt"] for r, n in nums.items()}
    pr = {r: n["per"] for r, n in nums.items()}
    D = {"D_own": figure(sd, draw, it[ROW], it[COMPARATOR], groups),
         "C_own": figure(sd, draw, it[ROW], it[STEM_ROW], groups),
         "vs_row_c": figure(sd, draw, it[ROW], it[BOTH_ROW], groups),
         "b2_less_row_b": figure(sd, draw, it[COMPARATOR], it[STEM_ROW], groups)}
    pD = None
    if any(n["refused"] for n in nums.values()):
        pD = {"D_own": the_40(sd, draw, SN.paired_values(pr[ROW], pr[COMPARATOR], "G")),
              "C_own": the_40(sd, draw, SN.paired_values(pr[ROW], pr[STEM_ROW], "G"))}
    d_own = SN.paired_values(it[ROW], it[COMPARATOR], "G")
    neg_d = {k: -v for k, v in d_own.items()}
    gap = SN.paired_values(it[COMPARATOR], it[STEM_ROW], "G")
    ld_itt, ld_pass, ld_ref = loudar_g50(m, draw)
    own_cp = {k: v["G_cp50"] for k, v in it[ROW].items() if v and v.get("G_cp50") is not None}
    own_cp_pass = {k: v["G_cp50"] for k, v in pr[ROW].items() if v and v.get("G_cp50") is not None}
    loudar = loudar_rows(sd, draw, own_cp, ld_itt, sets_of)
    if nums[ROW]["refused"] or ld_ref:
        loudar["passing_only"] = loudar_rows(sd, draw, own_cp_pass, ld_pass, sets_of)["bp"]
    vr, vwhy = _hashed_rows(m, SV.rows_path(), SV.PHASE_OUTCOME, "rows_sha256")
    cr, cwhy = _hashed_rows(m, control_rows_path(), CONTROL_OUTCOME, "rows_sha256")
    ranks = {"S": dict(rank_beside(neg_d, (vr or {}).get("S"), groups["deciding"]), source=vwhy or "voice rows.json"),
             "Ux": dict(rank_beside(neg_d, (cr or {}).get("Ux"), groups["deciding"]),
                        source=cwhy or "the control's rows.json"),
             "label": "Spearman against -D_own on the 40; beside, never changes the code"}
    body = {"plan": PLAN, "row": ROW, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "renders": 0, "reproduce": repro,
            "checks": checks, "control": {"state": state, "code": (m.get(CONTROL_OUTCOME) or {}).get("code"),
                                          COVERAGE_FIELD: (m.get(CONTROL_OUTCOME) or {}).get(COVERAGE_FIELD)},
            "answers_sha256": {r: n["answers_sha256"] for r, n in nums.items()},
            "refusals": _tagged_refusals(nums, sets_of), "own_g": {r: RR.own_g(sd, draw, it[r]) for r in nums}}
    rows = {"D": D, "passing_only": pD, "loudar": loudar,
            "share_recovered": SE.share(sd, draw, neg_d, gap),
            "share_label": "Fieller's -D_own / (build 2 - row (b)) on the 40: the share of build 2's cost recovered",
            "ranks": ranks, "per_part": {"D_own": {tag(k): v for k, v in d_own.items()},
                                         "C_own": {tag(k): v for k, v in
                                                   SN.paired_values(it[ROW], it[STEM_ROW], "G").items()}}}
    P.save(rows_path(), dict(body, rows=rows))                # the rows are saved before the code is read
    code, cp, label, arms = read_codes(D, pD, checks)
    report = dict(body, rows=rows, xw=code, code=code["code"], passing_only=cp, label=label, arms=arms,
                  shrunk_label=arms["label"], next="to the user with both reads" if label else code["decides"])
    P.save(report_path(), report)
    for n in ("D_own", "C_own", "vs_row_c"):
        iv = D[n][DECIDING_ARM]["the_40"]
        print(f"{n} on the 40: {iv} -> {(D[n][DECIDING_ARM]['reading'] or {}).get('reading')}")
    lab = ", ".join(x for x in (label, arms["label"]) if x)
    print(f"FS-OWN READ: {code['code']}{' (' + lab + ')' if lab else ''}: {code['said']}. Next: {report['next']}; "
          f"sha256 {S.file_sha(report_path())}")


def cmd_reproduce(_args):
    """Zero renders: `reproduce` from the stored files, printed and saved (never overwritten)."""
    m = require_own(*PHASES["reproduce"])
    NT.never_overwrite(reproduce_path())
    from learn import pipeline_fix as P

    draw, sd = SE.context()
    r = reproduce(m, draw, sd)
    P.save(reproduce_path(), dict(r, plan=PLAN, renders=0, time=time.strftime("%Y-%m-%d %H:%M:%S")))
    for n, iv in r["figures"].items():
        print(f"{n}: {_iv(iv)}; exact {r['exact'][n]}; seen {r['seen'].get(n, '-')}")
    for n, v in r["seen_beside"].items():
        same = "to 3 places" if v["to_3_places"] else "differs"
        print(f"seen beside {n}: {_iv(v['iv'])} against {v['seen']}: {same}")
    print(f"FS-OWN REPRODUCE {'HOLDS' if r['holds'] else 'FAILS'}")


COMMANDS = {"check-score": cmd_check_score, "check-search": cmd_check_search, "search": cmd_search,
            "answers": cmd_answers, "score": cmd_score, "reproduce": cmd_reproduce, "read": cmd_read}


def main(argv=None):
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    for p_ in (str(root), str(root / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--shard", type=S._shard, default=(0, 1))
    ap.add_argument("--rerun", action="store_true",
                    help="search or score again, once, only the parts whose record refused (S1: then Cen)")
    args = ap.parse_args(argv)
    if args.cmd not in ("search", "score") and (args.shard != (0, 1) or args.rerun):
        ap.error(f"{args.cmd} takes no --shard or --rerun")
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
