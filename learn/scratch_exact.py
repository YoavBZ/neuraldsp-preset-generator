"""The exact-notes test: rows `xn-bank`, `xn-swap`, `xn-reread`, `xn-list` (`docs/scratch-search-plan.md` section 15;
ledger `preset-ladder` `phase_scratch_exact`, then `phase_scratch_exact_targets`, `phase_scratch_exact_answers_<row>`,
`phase_scratch_exact_outcome`).

On "bank guitars", where replay from samples is exact by construction, what share of the dry-guitar mismatch cost comes
from note reading (Basic Pitch) and what share from the replay? The bank guitar is each part's build 2 `tr-di`
(`phase_scratch_notes_dry_b2`). Each part's record is a target preset (another part's row (b) answer on the same amp,
projected onto the dims every step-1 branch searches, the part's Cen elsewhere) rendered through the bank guitar. Every
row searches against that record (its held half zeros in the search process) and is scored through the bank guitar on
the held half, at lag 0:

| Row | Dry guitar of the search |
|---|---|
| `xn-bank` | the bank guitar |
| `xn-swap` | the part's real DI (`note_replay.di_section`) |
| `xn-reread` | Basic Pitch re-reads the bank guitar; build 2's rule; `rebuild_redo` with the bank guitar as the DI |
| `xn-list` | the same rebuild from the bank guitar's exact note list (build 2's notes after its fixes, as played) |

    $MAIN -m learn.scratch_exact build                        # zero renders: xn-reread and xn-list, the four proofs
    $MAIN -m learn.scratch_exact score-check                  # A1: two parts of row (c) re-scored (about 24 renders)
    $MAIN -m learn.scratch_exact search-check                 # A1: two parts' first 10 evaluations (about 26 renders)
    $MAIN -m learn.scratch_exact targets --shard 0/3          # A2: record, second render, Cen (6 renders a part)
    $MAIN -m learn.scratch_exact floors --shard 0/3           # A3: the target through the three other guitars
    $MAIN -m learn.scratch_exact floors-real --shard 0/3      # A4: row (b)'s answer through the true DI and tr-di
    $MAIN -m learn.scratch_exact floor-read                   # A5 (zero renders): targets/records/floors .json
    # the hash PR: phase_scratch_exact_targets
    $MAIN -m learn.scratch_exact search --row xn-bank --shard 0/3 [--rerun]
    $MAIN -m learn.scratch_exact answers --row xn-bank        # zero renders -> phase_scratch_exact_answers_bank
    $MAIN -m learn.scratch_exact score --row xn-bank --shard 0/3 [--rerun]
    $MAIN -m learn.scratch_exact gate                         # zero renders, once: G1 on xn-bank and xn-swap
    $MAIN -m learn.scratch_exact read                         # zero renders, once: the paired costs, shares, code

Every command refuses unless this checkout runs main's code (this module and the six pinned files) and keys (the
`phase_scratch_exact*` keys; `scratch_search.on_main`), and main holds the draw, row (b)'s answers, build 2's hash and
this declaration. The search opens only the blanked record and the dry guitar: never `targets.json`, a target file,
`answers-fs-stem.json` or anything scored (`SEARCH_FORBIDDEN`, `search_open`). Stage 2's rows (`xn-reread`,
`xn-list`) search only after `gate` wrote a holding G1.

The pure parts (`target_partner`, `project_target`, `left_mic_on_every_branch`, `synthetic_part`, `xn_numbers`,
`deciding_bug`, `fieller_share`, `gate`, `XN_TABLE`, `xn_code`, `list_split`, the guards) are tested in
tests/test_scratch_exact.py on the light CI runner (no numpy), on synthetic keys.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import subprocess
import time

from learn import note_transcribe as NT
from learn import scratch_notes as SN
from learn import scratch_search as S

LEDGER_ID = S.LEDGER_ID                  # preset-ladder
PLAN = "docs/scratch-search-plan.md section 15"
KEY_PREFIX = "phase_scratch_exact"
PHASE = "phase_scratch_exact"            # the declaration (with the amendments and the user's Go 1)
PHASE_TARGETS = "phase_scratch_exact_targets"   # Phase A's hash PR: build, checks, targets, records, floors
PHASE_OUTCOME = "phase_scratch_exact_outcome"
BUILD2 = "b2"                            # the bank guitar's build
PHASE_BANK = "phase_scratch_notes_dry_b2"
PHASE_B2_ANSWERS = "phase_scratch_notes_answers_b2"
STEM_ROW = "fs-stem"                     # row (b): the targets' source and the real share's denominator
ROWS = ("xn-bank", "xn-swap", "xn-reread", "xn-list")
SHORT = {"xn-bank": "bank", "xn-swap": "swap", "xn-reread": "reread", "xn-list": "list"}
STAGES = {1: ("xn-bank", "xn-swap"), 2: ("xn-reread", "xn-list")}
BUILT = ("xn-reread", "xn-list")         # the guitars `build` makes
BANK_ARM = "tr-di"
REF = "xn-record"                        # the reference's name in the search records
DECIDING = SN.DECIDING                   # BKS+GOAT, the 40 (the user's Go 1); all 47 beside
SUBSETS = SN.SUBSETS
SMALL, BIG = S.SMALL, S.BIG              # 0.05, 0.10: they label only (`paired_reading`, `number_reading`)
ARMS = {"answer": "G", "shrunk": "G_shrunk"}   # the answer decides; shrunk beside
SCORED = ("answer", "cp50", "cp100", "cp200", "shrunk")   # with Cen, the six settings a part (no borrowed, no centre)
FIELDS = ("G", "G_cp50", "G_cp100", "G_cp200", "G_shrunk")
DECIDING_SETTINGS = ("cen", "answer")    # a zero or non-finite distance here is a bug: the read stops, to the user
CHECK_BUDGET = SN.CHECK_BUDGET           # 10
PINNED = ("learn/scratch_search.py", "learn/scratch_notes.py", "learn/note_transcribe.py", "learn/note_rebuild.py",
          "learn/note_fixes.py", "learn/bp_run.py")
CODE_FILES = ("learn/scratch_exact.py",) + PINNED
SEARCH_FORBIDDEN = ("targets.json", "answers-fs-stem.json", "floors.json", "rows.json", "report.json")
# gate.json is not forbidden: stage 2's search reads it through `gate_record` (N1); it holds no settings, only G1
SEARCH_FORBIDDEN_DIRS = ("target", "floors", "floors-real", "score", "score-rerun")
ROOM_KEYS = ("cabParameters/leftRoomActive", "cabParameters/leftRoomMicLevel")
LEFT_CAB, RIGHT_CAB = "cabParameters/leftCabActive", "cabParameters/rightCabActive"
LEFT_MIC = "cabParameters/leftMicType"
SHARE_GRID = (-4.0, 4.0, 801)            # Fieller's declared grid: r from -4 to +4 in steps of 0.01 ...
SHARE_TOL = 1e-6                         # ... each boundary bisected to this ...
SHARE_REACH = 1e6                        # ... and an end that touches the grid followed outward (doubling) to here
REREAD_F_NOTE = ("re-read F matches the re-read notes against the full post-fix list, notes the rebuild skipped "
                 "included, so it understates recall slightly; it is used only beside the read")


def answers_key(row):
    """(Pure.) A row's answers hash key: `phase_scratch_exact_answers_<bank|swap|reread|list>`."""
    if row not in ROWS:
        raise SystemExit(f"unknown row {row!r}: one of {list(ROWS)}")
    return f"{KEY_PREFIX}_answers_{SHORT[row]}"


def stage_of(row):
    return next(s for s, rows in STAGES.items() if row in rows)


# --- the target (pure) -----------------------------------------------------------------------------------------------------

def target_partner(p, cen_of):
    """(Pure.) The part's target partner: its first partner in the draw's order whose Cen differs from its own, or None.
    cen_of: {pkey: Cen settings}."""
    for q in p["partners"]:
        if cen_of.get(q) != p["cen"]["settings"]:
            return q
    return None


def _on(v):
    return str(v).lower() in ("true", "1")


def left_mic_on_every_branch(step1_names, cen):
    """(Pure.) T1: the left mic type is searched on every step-1 branch only when the left cab can never be switched
    off: stage A searches the left cab's switch whenever the right cab is on (`full_controls_c1b.rooms_dims`), so the
    right cab must be off in Cen and never searched in step 1, and the left cab on in Cen."""
    return _on(cen.get(LEFT_CAB)) and not _on(cen.get(RIGHT_CAB)) and RIGHT_CAB not in step1_names


def always_searched(step1_names, eq_names, cen):
    """(Pure.) T1's dims, in order and once each: step 1's space, the amp EQ, the left room; the left mic type only when
    `left_mic_on_every_branch`."""
    out = []
    for n in list(step1_names) + list(eq_names) + list(ROOM_KEYS) + \
            ([LEFT_MIC] if left_mic_on_every_branch(step1_names, cen) else []):
        if n not in out:
            out.append(n)
    return out


def project_target(answer, cen, names, cats=None):
    """(Pure.) The target: the part's own Cen with the partner's answer on `names`; a categorical value (in `cats`:
    {name: the part's own value list}) kept only when it is in the part's list, else Cen's. -> (target, report)."""
    out = dict(cen)
    dropped = {}
    for n in names:
        if n not in answer:
            dropped[n] = "not in the partner's answer"
            continue
        v = answer[n]
        if cats and n in cats and str(v) not in {str(x) for x in cats[n]}:
            dropped[n] = "not in the part's own value list"
            continue
        out[n] = v
    changed = sorted(k for k in set(out) | set(cen) if out.get(k) != cen.get(k))
    return out, {"projected": list(names), "dropped": dropped, "changed": changed}


def on_grid(names, kinds, partner_cen, cen):
    """(Pure.) The on-grid risk: the projected continuous keys where the partner's Cen equals the part's."""
    return sorted(n for n in names if kinds.get(n) in ("cont", "log") and n in cen and partner_cen.get(n) == cen.get(n))


def one_per_partner(partner_of):
    """(Pure.) The dependence read's parts: one part per target partner, the first by key. partner_of: {pkey: q}."""
    seen, out = set(), []
    for k in sorted(partner_of):
        q = partner_of[k]
        if q not in seen:
            seen.add(q)
            out.append(k)
    return out


def coverage(searched_names, changed):
    """(Pure.) Whether a search record's searched dims cover every key on which its target differs from Cen."""
    miss = sorted(set(changed) - set(searched_names))
    return {"covered": not miss, "missing": miss}


def synthetic_part(p):
    """(Pure.) The exact world's part: the draw's, at lag 0 (the record is rendered from the bank guitar, which sits
    on the DI section's timeline)."""
    return dict(p, lag=0)


def lag_check(d0, dm, dp):
    """(Pure.) The lag check: the record against the second target render reads exactly 0 on both halves at lag 0 and
    above 0 at lag -1 and +1. d0, dm, dp: {half: distance}."""
    return (all(v == 0.0 for v in d0.values()) and all(S.finite_pos(v) for v in dm.values())
            and all(S.finite_pos(v) for v in dp.values()))


# --- the numbers (pure) ----------------------------------------------------------------------------------------------------

def deciding_bug(held, deciding=DECIDING_SETTINGS):
    """(Pure.) The bug rule: a zero distance on any scored setting (ln 0), or a non-finite one on Cen or the answer.
    -> {name: "zero" | "non-finite"} (empty when none)."""
    bad = {}
    for k, v in held.items():
        try:
            f = float(v)
        except (TypeError, ValueError):
            f = math.nan
        if f == 0.0:
            bad[k] = "zero"
        elif k in deciding and not (math.isfinite(f) and f > 0):
            bad[k] = "non-finite"
    return bad


def xn_numbers(held):
    """(Pure.) One part's numbers: G = ln(answer / Cen), and the checkpoints' and the shrunk answer's ln(x / Cen).
    held: after `scratch_search.nonfinite_rule`, "cen" finite. No borrowed answer and no centre in this test."""
    c = held["cen"]
    out = {}
    for f, k in zip(FIELDS, SCORED):
        out[f] = math.log(held[k] / c) if k in held else None
    return out


def paired(new, old, field="G"):
    return SN.paired_values(new, old, field)


# --- the intervals' shapes (pure) ------------------------------------------------------------------------------------------

def wholly_above(iv):
    return bool(iv) and iv.get("lo90") is not None and iv["lo90"] > 0


def wholly_below(iv):
    return bool(iv) and iv.get("hi90") is not None and iv["hi90"] < 0


def spans_zero(iv):
    return bool(iv) and iv.get("lo90") is not None and iv.get("hi90") is not None and iv["lo90"] <= 0 <= iv["hi90"]


def fieller_share(iv_of, den_iv, grid=SHARE_GRID, tol=SHARE_TOL, reach=SHARE_REACH):
    """(Pure.) F1: the share num/den as every r whose interval of (num - r * den), from the per-part values through
    `set_rows`' BKS+GOAT pool (`iv_of(r)` -> {mean, lo90, hi90}), spans zero; never from the two marginal intervals.
    Undefined when den's interval reaches zero. Solved on the declared grid, each boundary bisected to `tol`, an end
    touching the grid followed outward by doubling to `reach`; when the point estimate (where the mean is 0) lies in
    no segment the grid found, the set is seeded there and followed outward both ways (a defined share wholly outside the
    grid never reads empty). The shape as it comes out: "bounded", "a ray", "two
    rays", "the whole line", "several pieces" or "empty on the grid". -> dict."""
    if not den_iv or den_iv.get("lo90") is None or den_iv.get("hi90") is None:
        return {"defined": False, "why": "no interval for the denominator"}
    if den_iv["lo90"] <= 0 <= den_iv["hi90"]:
        return {"defined": False, "why": "the denominator's interval reaches zero: the share is undefined"}
    cache = {}

    def inside(r):
        if r not in cache:
            iv = iv_of(r)
            cache[r] = spans_zero(iv)
        return cache[r]

    def bisect(out_r, in_r):
        a, b = out_r, in_r
        while abs(a - b) > tol:
            mid = (a + b) / 2
            if inside(mid):
                b = mid
            else:
                a = mid
        return b

    lo_r, hi_r, n = grid
    first_step = (hi_r - lo_r) / (n - 1)

    def follow(r0, sign):
        """From an inside point r0, outward: the boundary, or None (open to `reach`); steps from the grid's, doubling."""
        prev, step = r0, first_step
        while True:
            r = r0 + sign * step
            if abs(r) > reach:
                return None
            if not inside(r):
                return bisect(r, prev)
            prev, step = r, step * 2

    rs = [lo_r + (hi_r - lo_r) * i / (n - 1) for i in range(n)]
    flags = [inside(r) for r in rs]
    segs, i = [], 0
    while i < n:
        if not flags[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and flags[j + 1]:
            j += 1
        a = follow(rs[i], -1) if i == 0 else bisect(rs[i - 1], rs[i])
        b = follow(rs[j], +1) if j == n - 1 else bisect(rs[j + 1], rs[j])
        segs.append({"lo": a, "hi": b})
        i = j + 1
    m0, m1 = (iv_of(0.0) or {}).get("mean"), (iv_of(1.0) or {}).get("mean")
    est = m0 / (m0 - m1) if m0 is not None and m1 is not None and m0 != m1 else None

    def covers(s, r):
        return (s["lo"] is None or s["lo"] <= r) and (s["hi"] is None or r <= s["hi"])
    seeded = False
    if est is not None and math.isfinite(est) and abs(est) <= reach and inside(est) and \
            not any(covers(s, est) for s in segs):
        segs.append({"lo": follow(est, -1), "hi": follow(est, +1)})   # the mean is 0 at est: seeded there (review)
        segs.sort(key=lambda s: -math.inf if s["lo"] is None else s["lo"])
        seeded = True
    if not segs:
        shape = "empty on the grid"
    elif len(segs) == 1:
        s = segs[0]
        shape = ("the whole line" if s["lo"] is None and s["hi"] is None else
                 "a ray" if s["lo"] is None or s["hi"] is None else "bounded")
    elif len(segs) == 2 and segs[0]["lo"] is None and segs[1]["hi"] is None:
        shape = "two rays"
    else:
        shape = "several pieces"
    return {"defined": True, "estimate": est, "shape": shape, "segments": segs, "grid": list(grid), "tol": tol,
            "reach": reach, "seeded_at_estimate": seeded, "evaluations": len(cache)}


# --- the gate, the codes and the list split (pure) -------------------------------------------------------------------------

def gate(g_bank, d_swap):
    """(Pure.) G1: `xn-bank` reads "passes" against Cen (`number_reading` on the 40) and D_swap's 90% interval lies
    wholly above zero (the condition for the share to be defined; no bar)."""
    rd = S.number_reading(g_bank)
    return {"holds": rd == "passes" and wholly_above(d_swap), "xn_bank": rd, "d_swap_above_zero": wholly_above(d_swap),
            "g_bank": g_bank, "d_swap": d_swap}


XN_TABLE = (    # (code, when (the first that holds, on the 40, the answer arm), said, next)
    ("XN-insensitive", "the gate (G1) fails",
     "`xn-bank` does not pass against Cen, or D_swap is not shown above zero; the share is undefined and nothing is "
     "priced. The realism comparison is reported beside.", "to the user"),
    ("XN-anomaly", "D*'s interval wholly below zero", "the re-read guitar beats the exact one",
     "audited before anything is said"),
    ("XN-overshoot", "D_swap - D* wholly below zero",
     "re-reading bank audio costs more than the whole real-DI mismatch measured in the exact world",
     "audited before anything is said"),
    ("XN-reading", "D* wholly above zero; D_swap - D* not wholly above zero",
     "reading plus re-derivation's cost is shown; a remainder beyond it is not shown (upper end hi90 = {gap_hi})",
     "to the user with the share; xn-list says which"),
    ("XN-both", "D* and D_swap - D* both wholly above zero", "both cost; the share and its interval give the split",
     "to the user"),
    ("XN-rest", "D* spans zero; D_swap - D* wholly above zero",
     "reading's cost is not shown in the exact world; the test rules out a reading cost above D*'s hi90 = {star_hi}",
     "to the user; no route licensed"),
    ("XN-undecided", "anything else", "not decided; undecided is not failed", "to the user"),
)
XN_CODES = tuple(c for c, *_ in XN_TABLE)


def xn_table_guard():
    """Refuse unless XN_TABLE holds the seven declared codes in order and 0 < SMALL < BIG."""
    if XN_CODES != ("XN-insensitive", "XN-anomaly", "XN-overshoot", "XN-reading", "XN-both", "XN-rest",
                    "XN-undecided"):
        raise SystemExit("XN_TABLE's codes are not the seven declared, in order")
    if not 0 < SMALL < BIG:
        raise SystemExit("the thresholds are not 0 < SMALL < BIG")
    if not KEY_PREFIX.startswith("phase_scratch_") or KEY_PREFIX.startswith(("phase_fs", "phase_scratch_notes")):
        raise SystemExit(f"{KEY_PREFIX} sits under a guarded prefix")


def xn_code(gate_holds, d_star, d_gap):
    """(Pure.) XN_TABLE's code, the first row that holds. d_star: D* on the 40; d_gap: D_swap - D* on the 40 ({mean,
    lo90, hi90} or None). -> {code, reading, next}."""
    if not gate_holds:
        code = "XN-insensitive"
    elif wholly_below(d_star):
        code = "XN-anomaly"
    elif wholly_below(d_gap):
        code = "XN-overshoot"
    elif wholly_above(d_star) and not wholly_above(d_gap):
        code = "XN-reading"
    elif wholly_above(d_star) and wholly_above(d_gap):
        code = "XN-both"
    elif spans_zero(d_star) and wholly_above(d_gap):
        code = "XN-rest"
    else:
        code = "XN-undecided"
    row = next(r for r in XN_TABLE if r[0] == code)
    said = row[2].format(gap_hi=(d_gap or {}).get("hi90"), star_hi=(d_star or {}).get("hi90"))
    return {"code": code, "when": row[1], "reading": said, "next": row[3]}


def list_split(reading_proper, d_list):
    """(Pure.) `xn-list`'s rule, coded before any render: reading proper shown when G(xn-reread) - G(xn-list) lies
    wholly above zero; re-derivation shown when D_list does."""
    return {"reading_proper_shown": wholly_above(reading_proper), "re_derivation_shown": wholly_above(d_list),
            "reading_proper": reading_proper, "d_list": d_list}


def score_check_verdict(new, stored, names=("cen",) + SCORED):
    """(Pure.) S1's score check: on the six settings rows (c) and this test share (Cen, the answer, the three
    checkpoints, shrunk), every held value and render sha256 equals row (c)'s stored score file's. -> {passed, ...}."""
    bad = []
    for k in sorted(stored):
        a, b = new.get(k) or {}, stored[k]
        for nm in names:
            if nm not in (b.get("held") or {}) or nm not in (a.get("held") or {}):
                bad.append((k, nm, "missing"))
            elif a["held"][nm] != b["held"][nm] or a["render_sha256"][nm] != b["render_sha256"][nm]:
                bad.append((k, nm))
    return {"passed": not bad and set(new) == set(stored), "mismatches": bad, "settings": list(names)}


def xn_answer_parts(draw, recs, search_sha):
    """(Pure but for `search_sha`.) A row's answers from its search records: per part the answer, step 1's incumbents
    at 50, 100 and 200 and the shrunk answer (no borrowed answer, no centre); each refusal with why. -> (parts,
    refused)."""
    parts, refused = {}, {}
    for p in draw["parts"]:
        k = p["pkey"]
        r = recs[k]
        if "refused" in r:
            refused[k] = {"search": r["refused"]}
            continue
        ans = r["answer"]["settings"]
        cps = {f"cp{c}": (r["step1"]["checkpoints"].get(str(c)) or {}).get("settings") for c in S.CHECKPOINTS}
        parts[k] = {"select": r["answer"]["select"], "answer": ans, **cps,
                    "shrunk": S.shrunk(ans, p["cen"]["settings"], r["searched_dims"]),
                    "fallback": r.get("fallback"), "search_sha256": search_sha(k)}
    return parts, refused


def dry_refusal(recs, want):
    """(Pure.) Why a row's answers refuse, or None: every answered search record's dry guitar sha256 must be the
    build's for that part and row. want: {pkey: sha256}."""
    for k, r in sorted(recs.items()):
        if "refused" in r:
            continue
        if not want.get(k) or r.get("dry_sha256") != want[k]:
            return f"{k}: the search record's dry guitar is not the declared one"
    return None


def search_refusal(row, gate_rec):
    """(Pure.) Why a row may not search, or None: stage 2's rows wait for a holding G1 (N1)."""
    if row in STAGES[2]:
        if gate_rec is None:
            return f"{row} is stage 2: it searches only after `gate` (G1) has run"
        if not gate_rec.get("gate", {}).get("holds"):
            return f"{row} is stage 2 and G1 does not hold: nothing more runs; to the user"
    return None


def phase_a_refusal(lag_failed, not_reproduced):
    """(Pure.) Phase A's checks enforced (review nit 1): any part failing the lag check, or whose row (b) answer through
    the true DI does not reproduce row (b)'s stored score, stops `floor-read` (nothing written) and `search`; it goes
    to the user. -> refusal or None."""
    bad = []
    if lag_failed:
        bad.append(f"the lag check fails on {len(lag_failed)} part(s)")
    if not_reproduced:
        bad.append(f"row (b)'s answer does not reproduce its stored score on {len(not_reproduced)} part(s)")
    return "; ".join(bad) + ": a bug, to the user before any search" if bad else None


def keys_refusal(local, main):
    """(Pure.) Why this checkout's `phase_scratch_exact*` keys are not main's, or None."""
    a = {k: v for k, v in (local or {}).items() if k.startswith(KEY_PREFIX)}
    b = {k: v for k, v in (main or {}).items() if k.startswith(KEY_PREFIX)}
    if a != b:
        return f"this checkout's {sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))} differ from main's"
    return None


def field_refusal(entry, phase, field, sha):
    """(Pure.) Why a file may not be used, or None: main's `phase` record must hold its sha256 under `field`."""
    rec = (entry or {}).get(phase)
    if not isinstance(rec, dict) or not rec.get(field):
        return f"main's {phase} has no {field}: the hash PR first"
    if rec[field] != sha:
        return f"the file's sha256 {sha[:12]} is not main's {phase} {field} {rec[field][:12]}"
    return None


def is_forbidden(path):
    """(Pure.) Whether the search may not open `path`: SEARCH_FORBIDDEN's names, or anything under the target, floor
    or score folders."""
    path = pathlib.PurePath(path)
    return path.name in SEARCH_FORBIDDEN or any(part in SEARCH_FORBIDDEN_DIRS for part in path.parent.parts[-2:])


def search_open(path):
    """Every file the search reads of this test goes through here: a forbidden one refuses."""
    if is_forbidden(path):
        raise SystemExit(f"{pathlib.PurePath(path).name}: the search never opens it")
    return pathlib.Path(path)


# --- paths --------------------------------------------------------------------------------------------------------------------

def exact_dir():
    return S.fs_dir() / "exact"


def _f(pk):
    return pk.replace("/", "__")


def dry_path(row, pk):
    return exact_dir() / "dry" / row / f"{_f(pk)}.npy"


def build_path():
    return exact_dir() / "build.json"


def work_dir():
    return exact_dir() / "work"


def check_dir(kind):
    if kind not in ("check-score", "check-search"):
        raise ValueError(kind)
    return exact_dir() / kind


def target_path(pk):
    return exact_dir() / "target" / f"{_f(pk)}.json"


def record_path(pk):
    return exact_dir() / "record" / f"{_f(pk)}.npy"


def targets_path():
    return exact_dir() / "targets.json"


def records_path():
    return exact_dir() / "records.json"


def floor_path(kind, pk):
    if kind not in ("floors", "floors-real"):
        raise ValueError(kind)
    return exact_dir() / kind / f"{_f(pk)}.json"


def floors_path():
    return exact_dir() / "floors.json"


def search_path(row, pk):
    return exact_dir() / "search" / row / f"{_f(pk)}.json"


def start_path(row, pk):
    return exact_dir() / "start-ref" / row / f"{_f(pk)}.json"


def shared_path():
    return exact_dir() / "search" / "xn-list-shared.json"


def answers_path(row):
    return exact_dir() / f"answers-{row}.json"


def score_path(row, pk):
    return exact_dir() / "score" / row / f"{_f(pk)}.json"


def gate_path():
    return exact_dir() / "gate.json"


def rows_path():
    return exact_dir() / "rows.json"


def report_path():
    return exact_dir() / "report.json"


# --- the guards -----------------------------------------------------------------------------------------------------------------

def _git(*a):
    from learn import pipeline_fix as P

    return subprocess.run(["git", "-C", str(P.REPO), *a], capture_output=True, text=True)


def pinned_identity():
    """Phase 1's proof 3: each of CODE_FILES equal to origin/main's (git diff --quiet). -> {file: identical}."""
    return {f: _git("diff", "--quiet", "origin/main", "--", f).returncode == 0 for f in CODE_FILES}


def require_exact(*phases):
    """Refuse unless this checkout runs main's code and keys, and main holds the draw, row (b)'s answers, build 2's
    hash, this declaration and `phases`. -> main's `preset-ladder` entry."""
    from learn import note_replay as NR

    xn_table_guard()
    m = S.require_on_main(S.PHASE, S.PHASE_DRAW, S.phase_answers(STEM_ROW), PHASE_BANK, PHASE, *phases)
    bad = [f for f, ok in pinned_identity().items() if not ok]
    if bad:
        raise SystemExit(f"this checkout's {bad} differ from main's: run from merged code")
    why = keys_refusal(NR.ledger_entry(), m)
    if why:
        raise SystemExit(why)
    return m


def bank_build(m):
    """Build 2's record, refused unless its sha256 is main's phase_scratch_notes_dry_b2."""

    return NT.require_file_hash(m, PHASE_BANK, NT.build_path(BUILD2))


def require_xbuild(m, hashed=True):
    """This test's build record: its proofs held; with `hashed`, its sha256 main's phase_scratch_exact_targets'."""
    if not build_path().exists():
        raise SystemExit("no build.json (run `build` first)")
    if hashed:
        why = field_refusal(m, PHASE_TARGETS, "build_sha256", S.file_sha(build_path()))
        if why:
            raise SystemExit(why)
    b = json.loads(search_open(build_path()).read_text())
    if not b.get("proofs_hold"):
        raise SystemExit("build.json's proofs did not hold")
    return b


def require_checks(m=None):
    """Both checks ran and passed; with `m`, their result files' sha256 main's phase_scratch_exact_targets'."""
    res = {}
    for kind in ("check-score", "check-search"):
        p = check_dir(kind) / "result.json"
        if not p.exists():
            raise SystemExit(f"{kind} has not run")
        r = json.loads(p.read_text())
        if not r.get("passed"):
            raise SystemExit(f"{kind} did not pass: {r.get('mismatches')}")
        if m is not None:
            why = field_refusal(m, PHASE_TARGETS, kind.replace("-", "_") + "_sha256", S.file_sha(p))
            if why:
                raise SystemExit(why)
        res[kind] = r
    return res


def require_records(m):
    """records.json (the records' sha256, no settings), refused unless its sha256 is main's."""
    p = search_open(records_path())
    if not p.exists():
        raise SystemExit("no records.json (run `floor-read` first)")
    why = field_refusal(m, PHASE_TARGETS, "records_sha256", S.file_sha(p))
    if why:
        raise SystemExit(why)
    rec = json.loads(p.read_text())
    if "lag_failed" not in rec or "row_b_not_reproduced" not in rec:
        raise SystemExit("records.json holds no lag check or reproduction check: not floor-read's")
    why = phase_a_refusal(rec["lag_failed"], rec["row_b_not_reproduced"])
    if why:
        raise SystemExit(why)
    return rec


def require_targets(m):
    """targets.json (the targets and Cen's stored values), refused unless its sha256 is main's. Never in the search."""
    p = targets_path()
    if not p.exists():
        raise SystemExit("no targets.json (run `floor-read` first)")
    why = field_refusal(m, PHASE_TARGETS, "targets_sha256", S.file_sha(p))
    if why:
        raise SystemExit(why)
    return json.loads(p.read_text())


def require_answers(m, row):

    return NT.require_file_hash(m, answers_key(row), answers_path(row))


def gate_record():
    p = search_open(gate_path())                       # allowed: stage 2's search reads G1 here (N1)
    return json.loads(p.read_text()) if p.exists() else None


def guitar_shas(build, row):
    """{pkey: the dry guitar sha256 a row's search must use}."""
    return {k: r["guitars"][row]["sha256"] for k, r in build["parts"].items()}


def load_guitar(row, p, build, b2, sd):
    """A row's dry guitar for a part, float32, refused unless its sha256 is the declared one. -> (x32, sha256)."""
    import numpy as np

    from learn import note_replay as NR

    pk = p["pkey"]
    if row == "xn-bank":
        x32 = NT.load_dry(BANK_ARM, pk, b2)
    elif row == "xn-swap":
        x32 = NR.di_section(sd.units[(p["set"], p["unit"], p["amp"])]["prt"])
    else:
        x32 = np.load(search_open(dry_path(row, pk))).astype(np.float32)
    sha = build["parts"][pk]["guitars"][row]["sha256"]
    if S.npy_sha(x32) != sha:
        raise SystemExit(f"{pk}: {row}'s dry guitar is not the declared one")
    return x32, sha


def load_record(pk, records):
    """The record (float64), refused unless its file's sha256 is records.json's."""
    import numpy as np

    path = search_open(record_path(pk))
    if S.file_sha(path) != records["parts"][pk]["file_sha256"]:
        raise SystemExit(f"{pk}: the record is not the hashed one")
    return np.load(path).astype(np.float64)


def load_record_blank(p, records):
    """The record with every sample outside the part's search half set to zeros (`scratch_search.blank_plan`); the
    unblanked array is dropped before the search sees anything."""
    from analysis.aligned import SAMPLE_RATE

    from learn import knob_ceiling as K

    ref = load_record(p["pkey"], records)
    for lo, hi in S.blank_plan(len(ref), p["search"], K.R.HALVES, SAMPLE_RATE):
        ref[lo:hi] = 0.0
    return ref


def _trim():
    from learn import pretrain_set as PS

    return int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR)


def disk_guard():
    from learn import pretrain_set as PS
    from learn import trusted_data as T

    if PS.free_gb() < T.DISK_GUARD_GB:
        raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")


def context():
    """The draw (hash-checked, no ruled-out DI), C3r's state, the replay's parts by key."""
    from learn import note_replay as R

    draw = SN.notes_draw()
    sd = R.Stored()
    if sd.st["sha256"] != draw["c3r_sha256"]:
        raise SystemExit("C3r's state changed since the draw")
    return draw, sd


def mine(draw, shard):
    k, n = shard
    return [p for j, p in enumerate(sorted(draw["parts"], key=lambda p: p["pkey"])) if j % n == k]


def target_dims(p, lists):
    """T1's dims for a part (from the code, not from any search record), the kinds of the step-1 dims and the part's own
    value list for the left mic type. -> (names, kinds, cats, step-1 names)."""
    from learn import full_controls as F
    from learn import knob_ceiling as K

    cen = p["cen"]["settings"]
    dims1 = F.c1a_space(p["amp"], F.c1a_start(cen, p["amp"]))
    s1 = [d.name for d in dims1]
    eq = [d.name for d in K.eq_space(p["amp"])]
    names = always_searched(s1, eq, cen)
    kinds = {d.name: d.kind for d in dims1}
    kinds.update({d.name: d.kind for d in K.eq_space(p["amp"])})
    kinds.update({ROOM_KEYS[0]: "switch", ROOM_KEYS[1]: "cont", LEFT_MIC: "cat"})
    cats = {LEFT_MIC: sorted({str(v) for v in lists[p["amp"]][LEFT_MIC.split("/")[1]]} | {str(cen.get(LEFT_MIC))},
                             key=int)}
    return names, kinds, cats, s1


# --- build (zero renders) ------------------------------------------------------------------------------------------------------

def cmd_build(_args):
    """Phase 1 (zero renders), once: per part, the bank guitar's exact note list (build 2's notes after its fixes, as
    played) and `xn-list` (`rebuild_redo` from that list with the bank guitar as the DI); Basic Pitch re-reads the bank
    guitar (no pre-roll) and `xn-reread` is built by build 2's rule with the bank guitar as the DI. The four proofs:
    (1) today's code rebuilds build 2's files byte for byte (`note_fixes.identity_check`); (2) the re-read's events
    equal build 2's round trip (`work/build-b2/round-trip/`) exactly; (3) the six pinned files and this module equal
    main's; (4) `xn-reread`'s pause shares per half (report, beside the bank guitar's stored maximum). Proofs 1 to 3
    must hold before anything is written. -> dry/<row>/<part>.npy, build.json."""
    m = require_exact()
    NT.never_overwrite(build_path())
    import numpy as np

    from analysis import aligned as A

    from learn import knob_ceiling as K
    from learn import note_fixes as NF
    from learn import note_rebuild as NR
    from learn import note_replay as R
    from learn import pipeline_fix as P

    _, why = NT.redo_on_main()
    if why:
        raise SystemExit(why)
    b2 = bank_build(m)
    _draw, sd = context()
    t0 = time.time()
    pinned = pinned_identity()
    if not all(pinned.values()):
        raise SystemExit(f"proof 3: {[f for f, ok in pinned.items() if not ok]} differ from main's")
    ident = NF.identity_check(BUILD2, b2["fixes"])
    if not ident["identical"]:
        raise SystemExit(f"proof 1: build 2 does not rebuild byte for byte: {ident['mismatches'][:5]}")
    fixes, ring, loud = b2["fixes"], b2["ring_variant"], b2.get("loud_gamma")
    pair = NT.install_pair(NT.load_manifest())
    excl, _, _, _ = NT._dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    todo = NT.build_todo(pair, NT.ear_items_file(BUILD2))
    order = [(kind, key, arm) for kind, key, *_ in todo for arm in NR.REDO_ARMS]
    parts = [t for t in todo if t[0] == "part"]
    rt_dir = NT.build_work_dir(BUILD2) / "round-trip"
    built, jobs = {}, []
    for kind, key, info, rec, di, finish in parts:
        bank32 = NT.load_dry(BANK_ARM, key, b2)
        bank64 = np.asarray(bank32, np.float64)
        notes, _ = NT.timed_notes(rec, di)
        exact, _ = NF.apply_fixes(notes, fixes, di)
        y_list, rep_list = NR.rebuild_redo(BANK_ARM, exact, len(bank64), bank, bank64, ring, finish=finish, loud=loud)
        built[key] = {"bank32": bank32, "bank64": bank64, "di": di, "finish": finish, "exact": exact,
                      "xn-list": (np.asarray(y_list, np.float32), rep_list),
                      "rt": rt_dir / f"{order.index(('part', key, BANK_ARM)):03d}-{BANK_ARM}.json"}
        jobs.append((bank32, BANK_ARM))
    import soundfile as sf

    reread = NT.run_bp(jobs, work_dir() / "reread")
    rt_bad, wav_same = [], 0
    for j, ((kind, key, *_), r) in enumerate(zip(parts, reread)):
        b = built[key]
        stored = json.loads(b["rt"].read_text())
        if r["events"] != stored["events"]:
            rt_bad.append(key)
        # the input files' sha256 differ by libsndfile's PEAK-chunk timestamp alone: the samples are compared instead
        mine_wav, rt_wav = work_dir() / "reread" / f"{j:03d}-{BANK_ARM}.wav", b["rt"].with_suffix(".wav")
        if rt_wav.exists() and np.array_equal(sf.read(str(mine_wav), dtype="float32")[0],
                                              sf.read(str(rt_wav), dtype="float32")[0]):
            wav_same += 1
        rnotes, trep = NT.timed_notes({"events": r["events"], "pre_s": 0.0}, b["bank64"])
        rfixed, frep = NF.apply_fixes(rnotes, fixes, b["bank64"])
        y_re, rep_re = NR.rebuild_redo(BANK_ARM, rfixed, len(b["bank64"]), bank, b["bank64"], ring, finish=b["finish"],
                                       loud=loud)
        b["xn-reread"] = (np.asarray(y_re, np.float32), rep_re)
        b["reread_f"] = {k: v for k, v in NT.match_notes(b["exact"], rfixed).items() if k != "ref_matched"}
        b["reread_f_prefix"] = {k: v for k, v in NT.match_notes(b["exact"], rnotes).items() if k != "ref_matched"}
        b["reread_timing"] = {**trep, "fixes": frep}
    if rt_bad:
        raise SystemExit(f"proof 2: {len(rt_bad)} re-read(s) differ from build 2's round trip: nothing written")
    lo, hi = _trim()
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "renders": 0, "bank_build": BUILD2,
           "bank_build_sha256": NR.file_sha(NT.build_path(BUILD2)), "fixes": fixes, "ring_variant": ring,
           "loud_gamma": loud, "reread_f_note": REREAD_F_NOTE, "parts": {}}
    pause_max = {"xn-reread": {h: 0.0 for h in K.R.HALVES}, "bank_stored": {h: 0.0 for h in K.R.HALVES}}
    for kind, key, info, rec, di, finish in parts:
        b = built[key]
        bank_sha = b2["parts"][key]["arms"][BANK_ARM]["sha256"]
        true32 = R.di_section(sd.units[(info["set"], info["unit"], info["amp"])]["prt"])
        if S.npy_sha(true32) != S.npy_sha(np.asarray(di, np.float32)):
            raise SystemExit(f"{key}: the build's DI is not this part's note_replay.di_section")
        row = {"guitars": {"xn-bank": {"sha256": bank_sha}, "xn-swap": {"sha256": S.npy_sha(true32)}},
               "notes": len(b["exact"]), "reread_f": b["reread_f"], "reread_f_before_fixes": b["reread_f_prefix"],
               "reread_timing": b["reread_timing"], "round_trip_equal": True}
        for g in BUILT:
            y32, rep = b[g]
            if len(y32) != len(di) or not np.isfinite(y32).all():
                raise SystemExit(f"{key}: a bad {g} dry guitar")
            path = dry_path(g, key)
            NT.never_overwrite(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            np.save(path, y32)
            sha = NR.file_sha(path)
            d = np.asarray(y32, np.float64)
            row["guitars"][g] = {"sha256": sha, "identical_to_bank": sha == bank_sha, "report": rep,
                                 "figures": NR.figures(b["bank64"], d)}
        pauses = {h: {str(n): {"xn-reread": float(NT.judge_pause_share(np.asarray(b["xn-reread"][0], np.float64)[lo:hi],
                                                                       0, h, n)),
                               "xn-bank": float(NT.judge_pause_share(b["bank64"][lo:hi], 0, h, n))}
                      for n in A.FRAME_SIZES} for h in K.R.HALVES}
        row["pauses"] = pauses
        stored = ((b2["parts"][key]["arms"][BANK_ARM].get("figures") or {}).get("judge-accepts") or {}).get("pauses") or {}
        for h in K.R.HALVES:
            pause_max["xn-reread"][h] = max(pause_max["xn-reread"][h], *(v["xn-reread"] for v in pauses[h].values()))
            pause_max["bank_stored"][h] = max([pause_max["bank_stored"][h]] +
                                              [v["dry"] for v in (stored.get(h) or {}).values()])
        out["parts"][key] = row
    ident_list = sorted(k for k, r in out["parts"].items() if r["guitars"]["xn-list"]["identical_to_bank"])
    out["proofs"] = {"identity": {"checked": ident["checked"], "identical": ident["identical"]},
                     "round_trip": {"parts": len(parts), "events_differ": len(rt_bad), "input_samples_equal": wav_same},
                     "pinned": pinned, "pause_max_by_half": pause_max}
    out["proofs_hold"] = ident["identical"] and not rt_bad and all(pinned.values())
    out["xn_list_identical_to_bank"] = len(ident_list)
    out["seconds"] = round(time.time() - t0, 1)
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    NT.never_overwrite(build_path())
    P.save(build_path(), out)
    fs = sorted(r["reread_f"]["f"] for r in out["parts"].values() if r["reread_f"]["f"] is not None)
    print(f"XN BUILD: {len(out['parts'])} parts; proofs: identity {ident['checked']} files identical, round trip "
          f"events {len(parts) - len(rt_bad)} of {len(parts)} equal (inputs {wav_same} of {len(parts)} sample-equal), "
          f"pinned {sum(pinned.values())} of {len(pinned)}; xn-reread pause max by "
          f"half {pause_max['xn-reread']} (bank stored {pause_max['bank_stored']}); xn-list identical to the bank "
          f"guitar on {len(ident_list)}; re-read F median {fs[len(fs) // 2] if fs else None}; "
          f"{out['seconds']} s; sha256 {S.file_sha(build_path())}")


# --- the start reference and the score (renders) ---------------------------------------------------------------------------

def start_reference(dry, p, x32, ref_blank, new_renderer, path, dry_sha):
    """`scratch_notes.start_reference`'s rule with the row's own dry name: the exact first evaluation step 1 asks for
    through the row's dry guitar in its own fresh primed process (2 renders), judged on the search half at the part's
    lag as `run_part` judges, written once (an existing file for the same dry guitar is the reference). -> (value,
    renders)."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import full_controls as F
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import pipeline_fix as P

    if path.exists():
        rec = json.loads(path.read_text())
        if rec["dry_sha256"] != dry_sha:
            raise SystemExit(f"{path.name}: a start reference for another dry guitar")
        return rec["value"], 0
    lo, hi = _trim()
    dj = np.asarray(x32, np.float64)[lo:hi]
    xs = SN.first_evaluation(p)
    if xs != LO.tdict(LO.sdict(F.c1a_start(p["cen"]["settings"], p["amp"]))):
        raise SystemExit(f"{p['pkey']}: the first evaluation is not run_part's priming sx1(start): an amendment first")
    y = np.asarray(AM.fresh_render(new_renderer, x32, p["cen"]["select"], xs, xs), np.float64)[lo:hi]
    v = R.half_distance(ref_blank, y, dj, p["lag"], p["search"]) if np.isfinite(y).all() else math.inf
    P.save(path, {"plan": PLAN, "part": p["pkey"], "dry": dry, "dry_sha256": dry_sha, "lag": p["lag"], "value": v,
                  "render_sha256": AM.audio_sha(np.nan_to_num(y)), "renders": 2,
                  "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    return v, 2


def score_exact_part(p, a, di32, ref, lag, cen_stored, new_renderer, names=SCORED):
    """One part's score: Cen and `names`' settings through `di32`, each primed alone (`fresh_render`), judged on the
    held half against `ref` with `di32` as the judge's DI at `lag`; the scoring control (a determinism check) against
    `cen_stored`. As `scratch_search.score_row_part` without the borrowed answers and the centre; the score check runs
    it with the true DI, the clean record, the part's lag and C3r's stored Cen. -> (the record, renders)."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import note_replay as NR

    lo, hi = _trim()
    di = np.asarray(di32, np.float64)[lo:hi]
    sets = {"cen": p["cen"]["settings"], **{k: a[k] for k in names if a.get(k) is not None}}
    done, held, shas, renders = {}, {}, {}, 0
    for name, s in sets.items():
        x = LO.tdict(s)
        kk = K.key(x)
        if kk not in done:
            y = np.asarray(AM.fresh_render(new_renderer, di32, a["select"], x, x), np.float64)[lo:hi]
            renders += 2
            done[kk] = (NR.half_distance(ref, y, di, lag, p["held"]) if np.isfinite(y).all() else math.inf,
                        AM.audio_sha(np.nan_to_num(y)))
        held[name], shas[name] = done[kk]
    ctl = S.finite_pos(held["cen"]) and S.finite_pos(cen_stored) and abs(math.log(held["cen"] / cen_stored)) <= \
        S.SCORE_TOL
    return ({"plan": PLAN, "part": p["pkey"], "held": held, "render_sha256": shas, "cen_stored": cen_stored,
             "scoring_control_ok": ctl, "lag": lag, "distinct_renders": len(done)}, renders)


# --- Phase A: the checks (renders, once) ---------------------------------------------------------------------------------

def cmd_score_check(_args):
    """A1 (about 24 renders), once: the first BKS and the first GOAT part of row (c)'s hashed answers re-scored through
    `score_exact_part` with the true DI, the clean record, the part's lag and C3r's stored Cen; on the six shared
    settings every held value and render sha256 must equal row (c)'s stored score file (S1). -> check-score/."""
    require_exact()
    d = check_dir("check-score")
    NT.never_overwrite(d / "result.json")
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import pipeline_fix as P

    R.no_separation_beside()
    draw, sd = context()
    ans = SN.comparator_answers()
    by = {p["pkey"]: p for p in draw["parts"]}
    LO._wait_cap()
    new, stored, total = {}, {}, 0
    for k in SN.check_parts(draw["parts"]):
        out = d / f"{_f(k)}.json"
        NT.never_overwrite(out)
        p = by[k]
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        clean = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        rec, used = score_exact_part(p, ans["parts"][k], R.di_section(prt), clean, p["lag"],
                                     sd.cen_judge((p["set"], p["unit"], p["amp"]))[p["held"]], CB.new_renderer)
        total += used
        P.save(out, rec)
        new[k], stored[k] = rec, json.loads(S.score_path(SN.COMPARATOR, k).read_text())
    res = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "renders": total, **score_check_verdict(new, stored),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(d / "result.json", res)
    print(f"XN SCORE-CHECK {'PASS' if res['passed'] else 'FAIL'}: {total} renders; mismatches {res['mismatches']}")


def cmd_search_check(_args):
    """A1 (about 26 renders), once: on the same two parts, this module's start reference and `scratch_search.run_part`
    with row (c)'s inputs (avg+mild, `xlnoG@-3` blanked, the part's lag) and a step-1 budget of CHECK_BUDGET, stopped
    after step 1; the evaluations must equal the start of row (c)'s stored curve exactly. -> check-search/."""
    require_exact()
    d = check_dir("check-search")
    NT.never_overwrite(d / "result.json")
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import pipeline_fix as P

    R.no_separation_beside()
    draw, sd = context()
    blur = json.loads((R.replay_dir() / "blur.json").read_text())
    if blur["draw_sha256"] != draw["replay_draw_sha256"]:
        raise SystemExit("blur.json was made from another replay draw")
    by, rby = {p["pkey"]: p for p in draw["parts"]}, {p["pkey"]: p for p in R.require_draw()["parts"]}
    lists = C.mic_lists()
    LO._wait_cap()
    new, stored, total = {}, {}, 0
    for k in SN.check_parts(draw["parts"]):
        out = d / f"{_f(k)}.json"
        NT.never_overwrite(out)
        p = by[k]
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        x32 = R.load_dry("avg+mild", rby[k], R.di_section(prt), blur)
        sha = blur["parts"][k]["sha256"]["avg+mild"]
        ref_blank = S.load_ref_blank(sd, p, "xlnoG")
        sref, used = start_reference("avg+mild", p, x32, ref_blank, CB.new_renderer, d / "start-ref" / f"{_f(k)}.json",
                                     sha)
        rec = S.run_part(p, "avg+mild", "xlnoG", x32, ref_blank, CB.new_renderer, lists, budget=CHECK_BUDGET,
                         start_ref=sref, dry_sha256=sha, step1_only=True)
        total += rec.get("renders", 0) + used
        P.save(out, rec)
        new[k], stored[k] = rec, json.loads(S.search_path(SN.COMPARATOR, k).read_text())
    res = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASE}", "renders": total, "budget": CHECK_BUDGET,
           **SN.search_check_verdict(new, stored), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(d / "result.json", res)
    print(f"XN SEARCH-CHECK {'PASS' if res['passed'] else 'FAIL'}: {total} renders; mismatches {res['mismatches']}")


# --- Phase A: the targets and the floors (renders) ---------------------------------------------------------------------------

def cmd_targets(args):
    """A2 (6 renders a part): per part the target (`target_partner`, `project_target` on T1's dims), then through the
    bank guitar, each primed alone: the record, a second target render and Cen; the lag check (`lag_check`, zero
    renders) and Cen's distance on both halves (the scoring control's stored value). -> target/<part>.json,
    record/<part>.npy."""
    m = require_exact()
    require_checks()
    require_xbuild(m, hashed=False)
    b2 = bank_build(m)
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import pipeline_fix as P

    R.no_separation_beside()
    draw, sd = context()
    ans_b = S.require_hash(S.phase_answers(STEM_ROW), S.answers_path(STEM_ROW))
    cen_of = {q["pkey"]: q["cen"]["settings"] for q in draw["parts"]}
    lists = C.mic_lists()
    lo, hi = _trim()
    LO._wait_cap()
    total, t0 = 0, time.time()
    for p in mine(draw, args.shard):
        pk = p["pkey"]
        out = target_path(pk)
        if out.exists():
            continue
        disk_guard()
        NT.never_overwrite(record_path(pk))
        q = target_partner(p, cen_of)
        if q is None:
            raise SystemExit(f"{pk}: no partner with another Cen")
        names, kinds, cats, s1 = target_dims(p, lists)
        qa = ans_b["parts"][q]
        target, rep = project_target(qa["answer"], p["cen"]["settings"], names, cats)
        bank32 = NT.load_dry(BANK_ARM, pk, b2)
        dj = np.asarray(bank32, np.float64)[lo:hi]
        sel = p["cen"]["select"]
        xt, xc = LO.tdict(target), LO.tdict(p["cen"]["settings"])
        y1 = np.asarray(AM.fresh_render(CB.new_renderer, bank32, sel, xt, xt), np.float64)[lo:hi]
        y2 = np.asarray(AM.fresh_render(CB.new_renderer, bank32, sel, xt, xt), np.float64)[lo:hi]
        yc = np.asarray(AM.fresh_render(CB.new_renderer, bank32, sel, xc, xc), np.float64)[lo:hi]
        total += 6
        if not (np.isfinite(y1).all() and np.isfinite(y2).all() and np.isfinite(yc).all()):
            raise SystemExit(f"{pk}: a non-finite target or Cen render: a bug, to the user")
        d0 = {h: R.half_distance(y1, y2, dj, 0, h) for h in K.R.HALVES}
        dm = {h: R.half_distance(y1, y2, dj, -1, h) for h in K.R.HALVES}
        dp = {h: R.half_distance(y1, y2, dj, 1, h) for h in K.R.HALVES}
        dc = {h: R.half_distance(y1, yc, dj, 0, h) for h in K.R.HALVES}
        record_path(pk).parent.mkdir(parents=True, exist_ok=True)
        np.save(record_path(pk), y1)
        P.save(out, {"plan": PLAN, "part": pk, "partner": q, "partner_index": p["partners"].index(q),
                     "partner_select": qa["select"], "select": sel, "target": target, **rep,
                     "on_grid": on_grid(names, kinds, cen_of[q], p["cen"]["settings"]),
                     "target_equals_cen": sorted(n for n in names if kinds.get(n) in ("cont", "log")
                                                 and target.get(n) == p["cen"]["settings"].get(n)),
                     "left_mic_projected": LEFT_MIC in names, "step1_names": s1,
                     "bank_sha256": b2["parts"][pk]["arms"][BANK_ARM]["sha256"],
                     "build_sha256": S.file_sha(build_path()),
                     "record_file_sha256": S.file_sha(record_path(pk)), "record_audio_sha256": AM.audio_sha(y1),
                     "second_audio_sha256": AM.audio_sha(y2), "cen_audio_sha256": AM.audio_sha(yc),
                     "lag0": d0, "lag_minus1": dm, "lag_plus1": dp, "lag_ok": lag_check(d0, dm, dp),
                     "cen": dc, "cen_held": dc[p["held"]], "renders": 6, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"{pk[-50:]}: target {len(rep['changed'])} keys from Cen; lag check {'ok' if lag_check(d0, dm, dp) else 'FAIL'}"
              f"; Cen held {dc[p['held']]:.5g}; {total} renders, {time.time() - t0:.0f} s", flush=True)
    print(f"XN TARGETS DONE {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s")


def cmd_floors(args):
    """A3 (6 renders a part): at the target preset, the true DI, `xn-reread` and `xn-list`, each primed alone, judged on
    both halves against the record with the bank guitar as the judge's DI at lag 0; ln(d / d_Cen) on the held half.
    A fixed-preset floor: an upper bound on what search cannot recover, read for order and rough size only (A1).
    -> floors/<part>.json."""
    m = require_exact()
    build = require_xbuild(m, hashed=False)
    b2 = bank_build(m)
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import pipeline_fix as P

    R.no_separation_beside()
    draw, sd = context()
    lo, hi = _trim()
    LO._wait_cap()
    total, t0 = 0, time.time()
    for p in mine(draw, args.shard):
        pk = p["pkey"]
        out = floor_path("floors", pk)
        if out.exists():
            continue
        disk_guard()
        t = json.loads(target_path(pk).read_text())
        if t["record_file_sha256"] != S.file_sha(record_path(pk)):
            raise SystemExit(f"{pk}: the record is not the target step's")
        ref = np.load(record_path(pk)).astype(np.float64)
        dj = np.asarray(NT.load_dry(BANK_ARM, pk, b2), np.float64)[lo:hi]
        xt = LO.tdict(t["target"])
        rec = {"plan": PLAN, "part": pk, "guitars": {}}
        for g in ("xn-swap",) + BUILT:
            x32, _sha = load_guitar(g, p, build, b2, sd)
            y = np.asarray(AM.fresh_render(CB.new_renderer, x32, t["select"], xt, xt), np.float64)[lo:hi]
            total += 2
            d = {h: (R.half_distance(ref, y, dj, 0, h) if np.isfinite(y).all() else math.inf) for h in K.R.HALVES}
            dh = d[p["held"]]
            rec["guitars"][g] = {"d": d, "audio_sha256": AM.audio_sha(np.nan_to_num(y)),
                                 "floor": (math.log(dh / t["cen_held"]) if S.finite_pos(dh) else None),
                                 "zero": dh == 0.0}
        rec.update(renders=6, time=time.strftime("%Y-%m-%d %H:%M:%S"))
        P.save(out, rec)
        print(f"{pk[-50:]}: floors {[(g, v['floor']) for g, v in rec['guitars'].items()]}; {total} renders", flush=True)
    print(f"XN FLOORS DONE {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s")


def cmd_floors_real(args):
    """A4 (4 renders a part), a declared read of real held halves: row (b)'s stored answer through the true DI (its
    render sha256 and held value must reproduce row (b)'s stored score) and through the bank guitar (`tr-di`), each
    judged on the held half against the clean record with the true DI as the judge's DI at the part's lag; the real
    analogue ln(d_tr-di / Cen's stored value). -> floors-real/<part>.json."""
    m = require_exact()
    b2 = bank_build(m)
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import pipeline_fix as P

    R.no_separation_beside()
    draw, sd = context()
    ans_b = S.require_hash(S.phase_answers(STEM_ROW), S.answers_path(STEM_ROW))
    lo, hi = _trim()
    LO._wait_cap()
    total, t0 = 0, time.time()
    for p in mine(draw, args.shard):
        pk = p["pkey"]
        out = floor_path("floors-real", pk)
        if out.exists():
            continue
        disk_guard()
        prt = sd.units[(p["set"], p["unit"], p["amp"])]["prt"]
        di32 = R.di_section(prt)
        di = np.asarray(di32, np.float64)[lo:hi]
        clean = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
        a = ans_b["parts"][pk]
        x = LO.tdict(a["answer"])
        stored = json.loads(S.score_path(STEM_ROW, pk).read_text())
        cen_stored = sd.cen_judge((p["set"], p["unit"], p["amp"]))[p["held"]]
        rec = {"plan": PLAN, "part": pk, "cen_stored": cen_stored}
        for g, g32 in (("true", di32), (BANK_ARM, NT.load_dry(BANK_ARM, pk, b2))):
            y = np.asarray(AM.fresh_render(CB.new_renderer, g32, a["select"], x, x), np.float64)[lo:hi]
            total += 2
            dh = R.half_distance(clean, y, di, p["lag"], p["held"]) if np.isfinite(y).all() else math.inf
            rec[g] = {"held": dh, "audio_sha256": AM.audio_sha(np.nan_to_num(y)),
                      "ln_over_cen": math.log(dh / cen_stored) if S.finite_pos(dh) else None}
        rec["reproduces_row_b"] = (rec["true"]["held"] == stored["held"]["answer"]
                                   and rec["true"]["audio_sha256"] == stored["render_sha256"]["answer"])
        rec["tr_di_less_true"] = (math.log(rec[BANK_ARM]["held"] / rec["true"]["held"])
                                  if S.finite_pos(rec[BANK_ARM]["held"]) and S.finite_pos(rec["true"]["held"]) else None)
        rec.update(renders=4, time=time.strftime("%Y-%m-%d %H:%M:%S"))
        P.save(out, rec)
        print(f"{pk[-50:]}: row (b) reproduced {rec['reproduces_row_b']}; tr-di less true {rec['tr_di_less_true']}; "
              f"{total} renders", flush=True)
    print(f"XN FLOORS-REAL DONE {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s")


def _rows_of(sd, draw, vals, keys=None):
    r = SN.set_rows(sd, draw, {k: v for k, v in vals.items() if v is not None and math.isfinite(v)}, keys)
    return {"bks_goat": (r or {}).get("bks_goat"), "pool_47": (r or {}).get("deciding_pool"),
            "parts": len([v for v in vals.values() if v is not None and math.isfinite(v)])}


def cmd_floor_read(_args):
    """A5 (zero renders), once: every part's target, floor and real-floor files gathered into targets.json, records.json
    (the records' sha256 only, for the search) and floors.json, with the floor read on the 40 and all 47 (for order and
    rough size, never a predicted D): ln(d / d_Cen) per guitar in the exact world, and in the real world row (b)'s
    answer through `tr-di` and through the true DI against Cen. Their sha256, the build's and the checks' go into the
    ledger as phase_scratch_exact_targets (the hash PR) before any search."""
    m = require_exact()
    checks = require_checks()
    require_xbuild(m, hashed=False)
    for p_ in (targets_path(), records_path(), floors_path()):
        NT.never_overwrite(p_)
    from learn import pipeline_fix as P

    draw, sd = context()
    keys = sorted(p["pkey"] for p in draw["parts"])
    tg, fl, fr = {}, {}, {}
    for k in keys:
        for d, path in ((tg, target_path(k)), (fl, floor_path("floors", k)), (fr, floor_path("floors-real", k))):
            if not path.exists():
                raise SystemExit(f"{k}: {path.parent.name} not run")
            d[k] = json.loads(path.read_text())
        if tg[k]["record_file_sha256"] != S.file_sha(record_path(k)):
            raise SystemExit(f"{k}: the record changed since `targets`")
        if tg[k]["build_sha256"] != S.file_sha(build_path()):
            raise SystemExit(f"{k}: the target was made from another build")
    lag_bad = sorted(k for k in keys if not tg[k]["lag_ok"])
    repro_bad = sorted(k for k in keys if not fr[k]["reproduces_row_b"])
    why = phase_a_refusal(lag_bad, repro_bad)
    if why:                                              # nothing written: no hash PR, no search
        raise SystemExit(why)
    records = {"plan": PLAN, "build_sha256": S.file_sha(build_path()), "lag_failed": lag_bad,
               "row_b_not_reproduced": repro_bad,
               "parts": {k: {"file_sha256": tg[k]["record_file_sha256"], "audio_sha256": tg[k]["record_audio_sha256"]}
                         for k in keys}}
    targets = {"plan": PLAN, "build_sha256": S.file_sha(build_path()), "time": time.strftime("%Y-%m-%d %H:%M:%S"),
               "lag_ok": len(keys) - len(lag_bad), "lag_failed": lag_bad, "parts": tg}
    read = {"exact": {}, "real": {}}
    for g in ("xn-swap",) + BUILT:
        read["exact"][g] = _rows_of(sd, draw, {k: fl[k]["guitars"][g]["floor"] for k in keys})
        read["exact"][g]["zero_parts"] = sum(fl[k]["guitars"][g]["zero"] for k in keys)
    held_of = {p["pkey"]: p["held"] for p in draw["parts"]}
    read["exact"]["xn-bank"] = {"held_zero_parts": sum(tg[k]["lag0"][held_of[k]] == 0.0 for k in keys)}
    read["real"]["row_b_answer_true"] = _rows_of(sd, draw, {k: fr[k]["true"]["ln_over_cen"] for k in keys})
    read["real"]["row_b_answer_tr_di"] = _rows_of(sd, draw, {k: fr[k][BANK_ARM]["ln_over_cen"] for k in keys})
    read["real"]["tr_di_less_true"] = _rows_of(sd, draw, {k: fr[k]["tr_di_less_true"] for k in keys})
    partner_of = {k: tg[k]["partner"] for k in keys}
    floors = {"plan": PLAN, "time": targets["time"], "renders": {
        "targets": sum(tg[k]["renders"] for k in keys), "floors": sum(fl[k]["renders"] for k in keys),
        "floors_real": sum(fr[k]["renders"] for k in keys),
        "checks": checks["check-score"]["renders"] + checks["check-search"]["renders"]},
        "row_b_reproduced": len(keys) - len(repro_bad), "row_b_not_reproduced": repro_bad,
        "partners": len(set(partner_of.values())), "one_per_partner": one_per_partner(partner_of),
        "left_mic_projected_parts": sum(tg[k]["left_mic_projected"] for k in keys),
        "on_grid_counts": {k: len(tg[k]["on_grid"]) for k in keys},
        "target_changed_counts": {k: len(tg[k]["changed"]) for k in keys},
        "xn_swap_note": ("xn-swap's floor includes the true DI's input-level offset (the SB.measure clip, up to about "
                         "7 dB) at a fixed input gain, which the search can fix"),
        "read": read, "floors": fl, "floors_real": fr}
    P.save(targets_path(), targets)
    P.save(records_path(), records)
    P.save(floors_path(), floors)
    print(f"XN FLOOR-READ: lag check {targets['lag_ok']} of {len(keys)}; row (b) reproduced "
          f"{floors['row_b_reproduced']} of {len(keys)}; {floors['partners']} partners; renders {floors['renders']}")
    for side in read:
        for g, r in read[side].items():
            bg = (r.get("bks_goat") or {}).get("all") if isinstance(r, dict) else None
            print(f"  {side} {g}: on the 40 {bg}; all 47 {r.get('pool_47') if isinstance(r, dict) else None}")
    print(f"sha256: build {S.file_sha(build_path())}, check-score "
          f"{S.file_sha(check_dir('check-score') / 'result.json')}, check-search "
          f"{S.file_sha(check_dir('check-search') / 'result.json')}, targets {S.file_sha(targets_path())}, records "
          f"{S.file_sha(records_path())}, floors {S.file_sha(floors_path())} (into the ledger as {PHASE_TARGETS})")


# --- the rows: search, answers, score (renders but answers) --------------------------------------------------------------

def cmd_search(args):
    """One shard of a row's searches (renders), after the targets' hash PR: per part (sorted by key, every n-th) the
    row's dry guitar (its sha256 the build's), the record blanked outside the search half (records.json's sha256), the
    start reference at lag 0, then `scratch_search.search_row_part` on the exact world's part (`synthetic_part`). An
    `xn-list` guitar byte-identical to the bank guitar takes `xn-bank`'s search record (and its rerun) byte for byte.
    Stage 2 waits for a holding G1. The search opens none of SEARCH_FORBIDDEN. The disk guard before every part."""
    row = args.row
    m = require_exact(PHASE_TARGETS)
    require_checks(m)
    build = require_xbuild(m)
    records = require_records(m)
    why = search_refusal(row, gate_record())
    if why:
        raise SystemExit(why)
    b2 = bank_build(m)
    from learn import cc_build as CB
    from learn import full_controls_c1b as C
    from learn import local_objective as LO
    from learn import note_replay as R

    R.no_separation_beside()
    draw, sd = context()
    todo = mine(draw, args.shard)
    if args.first:
        todo = todo[:args.first]
    lists = C.mic_lists()
    LO._wait_cap()
    total, t0 = 0, time.time()
    for p in todo:
        pk = p["pkey"]
        out = search_path(row, pk)
        if getattr(args, "rerun", False):                # S1: a technical refusal, once more in this fresh process
            if not out.exists() or not S.refused_record(json.loads(out.read_text())):
                continue
            out = S.rerun_path(out)
        if out.exists():
            continue
        disk_guard()
        g = build["parts"][pk]["guitars"]
        if row == "xn-list" and g["xn-list"]["identical_to_bank"]:
            src = search_path("xn-bank", pk)
            if getattr(args, "rerun", False):
                src = S.rerun_path(src)
            if not src.exists():
                raise SystemExit(f"{pk}: xn-list's guitar is the bank guitar, and xn-bank's record is not there yet")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(src.read_bytes())
            print(f"{pk[-50:]}: xn-list identical to the bank guitar: xn-bank's record taken byte for byte", flush=True)
            continue
        x32, sha = load_guitar(row, p, build, b2, sd)
        ref_blank = load_record_blank(p, records)
        px = synthetic_part(p)
        spath = start_path(row, pk)
        if getattr(args, "rerun", False):
            spath = S.rerun_path(spath)
        sref, used = start_reference(row, px, x32, ref_blank, CB.new_renderer, spath, sha)
        rec = S.search_row_part(px, row, REF, x32, ref_blank, CB.new_renderer, lists, out, f"{LEDGER_ID} {PHASE}",
                                start_ref=sref, dry_sha256=sha)
        total += rec.get("renders", 0) + used
        if "refused" in rec:
            print(f"{pk[-50:]}: REFUSED {rec['refused']}", flush=True)
        print(f"{row} shard {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s "
              f"({total / max(1, time.time() - t0) * 3600:.0f} an hour)", flush=True)
    print(f"XN SEARCH DONE {row} {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s")


def cmd_answers(args):
    """A row's answers (zero renders): every search record or its rerun (`with_reruns`; a technical refusal not yet
    rerun waits), each dry guitar checked against the build (`dry_refusal`), `xn_answer_parts`, the refusals reported
    (S1), and per part whether the searched dims covered every key on which the target differs from Cen (T1).
    -> answers-<row>.json; its sha256 into the ledger as phase_scratch_exact_answers_<row> before `score`."""
    row = args.row
    m = require_exact(PHASE_TARGETS)
    build = require_xbuild(m)
    tg = require_targets(m)
    NT.never_overwrite(answers_path(row))
    from learn import pipeline_fix as P

    draw, _sd = context()
    for p in draw["parts"]:
        if not search_path(row, p["pkey"]).exists():
            raise SystemExit(f"{p['pkey']}: not searched")
    recs, used, reruns = S.with_reruns([p["pkey"] for p in draw["parts"]], lambda k: search_path(row, k))
    why = S.rerun_refusal(reruns)
    if why:
        raise SystemExit(why)
    why = dry_refusal(recs, guitar_shas(build, row))
    if why:
        raise SystemExit(why)
    parts, refused = xn_answer_parts(draw, recs, lambda k: S.file_sha(used[k]))
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    cov = {k: coverage([s["module"] + "/" + s["key"] for s in (recs[k].get("searched_dims") or [])],
                       tg["parts"][k]["changed"]) for k in parts}
    out = {"plan": PLAN, "row": row, "ref": REF, "draw_sha256": S.file_sha(S.draw_path()),
           "build_sha256": S.file_sha(build_path()), "time": time.strftime("%Y-%m-%d %H:%M:%S"),
           "renders": sum(r.get("renders", 0) for r in recs.values()), "refused": refused, "reruns": reruns,
           "refusal_report": S.refusal_report(refused, sets_of, DECIDING), "stopped": False,
           "coverage": {"covered": sum(c["covered"] for c in cov.values()), "parts": cov}, "parts": parts}
    P.save(answers_path(row), out)
    print(f"XN ANSWERS {row}: {len(parts)} parts, {len(refused)} refused (each reads at Cen); reruns {reruns}; "
          f"searched dims covered the target's keys on {out['coverage']['covered']} of {len(cov)}; sha256 "
          f"{S.file_sha(answers_path(row))} (into the ledger as {answers_key(row)} before `score`)")


def cmd_score(args):
    """One shard of a row's score (renders): Cen and the five settings of the hashed answers through the bank guitar,
    each primed alone, judged on the held half against the record at lag 0; the scoring control against Cen's value
    from `targets` (a determinism check). -> score/<row>/<part>.json."""
    row = args.row
    m = require_exact(PHASE_TARGETS, answers_key(row))
    records = require_records(m)
    tg = require_targets(m)
    ans = require_answers(m, row)
    b2 = bank_build(m)
    from learn import cc_build as CB
    from learn import local_objective as LO
    from learn import note_replay as R
    from learn import pipeline_fix as P

    R.no_separation_beside()
    draw, _sd = context()
    LO._wait_cap()
    total, t0 = 0, time.time()
    for p in mine(draw, args.shard):
        pk = p["pkey"]
        out = score_path(row, pk)
        a = ans["parts"].get(pk)
        if getattr(args, "rerun", False):                # S1: a scoring-control miss, once more in this fresh process
            if a is None or not out.exists() or json.loads(out.read_text())["scoring_control_ok"]:
                continue
            out = S.rerun_path(out)
        if a is None or out.exists():
            continue
        disk_guard()
        bank32 = NT.load_dry(BANK_ARM, pk, b2)
        ref = load_record(pk, records)
        rec, used = score_exact_part(synthetic_part(p), a, bank32, ref, 0, tg["parts"][pk]["cen_held"], CB.new_renderer)
        rec.update(row=row, answers_sha256=S.file_sha(answers_path(row)))
        total += used
        P.save(out, rec)
        print(f"{pk[-50:]}: scored {rec['distinct_renders']} settings; control "
              f"{'ok' if rec['scoring_control_ok'] else 'MISS'}; {total} renders, {time.time() - t0:.0f} s", flush=True)
    print(f"XN SCORE DONE {row} {args.shard[0]}/{args.shard[1]}: {total} renders in {time.time() - t0:.0f} s")


# --- the reads (zero renders) -----------------------------------------------------------------------------------------------

def read_xn_parts(draw, ans, answers_sha, row):
    """A row's per-part numbers from its score files: a scoring-control miss read from its rerun (S1; one not yet rerun
    waits), then a refusal; `deciding_bug` stops the read; `nonfinite_rule`; `xn_numbers`. -> (per, refused,
    replaced, misses)."""
    refused = dict(ans["refused"])
    per, replaced, ctl = {}, {}, []
    for p in draw["parts"]:
        k = p["pkey"]
        if k not in ans["parts"]:
            per[k] = None
            continue
        sp = score_path(row, k)
        if not sp.exists():
            raise SystemExit(f"{row} {k}: not scored")
        sc = json.loads(sp.read_text())
        if not sc["scoring_control_ok"]:
            if not S.rerun_path(sp).exists():
                raise SystemExit(f"{row} {k}: a scoring-control miss not yet rerun: `score --rerun` first")
            again = json.loads(S.rerun_path(sp).read_text())
            if again["scoring_control_ok"]:
                sc = again
        if sc["answers_sha256"] != answers_sha:
            raise SystemExit(f"{row} {k}: scored from other answers")
        if not sc["scoring_control_ok"]:
            refused[k] = {"scoring_control": {"cen": sc["held"]["cen"], "stored": sc["cen_stored"]}}
            ctl.append(k)
            per[k] = None
            continue
        bug = deciding_bug(sc["held"])
        if bug:
            raise SystemExit(f"{row} {k}: {bug} — a zero or non-finite distance on a deciding setting is a bug: the "
                             "read stops, to the user")
        held, rep = S.nonfinite_rule(sc["held"])
        if rep:
            replaced[k] = rep
        per[k] = xn_numbers(held)
    return per, refused, replaced, ctl


def row_numbers(m, draw, row):
    ans = require_answers(m, row)
    per, refused, replaced, ctl = read_xn_parts(draw, ans, S.file_sha(answers_path(row)), row)
    return {"per": per, "itt": S.itt_per(per, refused, FIELDS), "refused": refused, "replaced": replaced,
            "control_misses": ctl, "coverage": ans.get("coverage"), "answers_sha256": S.file_sha(answers_path(row))}


def real_numbers(m, draw, sd):
    """Row (b)'s and build 2's real per-part numbers (intent-to-treat), each from its hashed answers and score files."""
    from learn import note_replay as R

    rby = {p["pkey"]: p for p in R.require_draw()["parts"]}
    b_ans = S.require_hash(S.phase_answers(STEM_ROW), S.answers_path(STEM_ROW))
    per_b, ref_b, *_ = S.read_row_parts(draw, b_ans, S.file_sha(S.answers_path(STEM_ROW)),
                                        lambda k: S.score_path(STEM_ROW, k), sd, rby)
    n_ans = NT.require_file_hash(m, PHASE_B2_ANSWERS, SN.answers_path(BUILD2))
    per_n, ref_n, *_ = S.read_row_parts(draw, n_ans, S.file_sha(SN.answers_path(BUILD2)),
                                        lambda k: SN.score_path(k, BUILD2), sd, rby)
    return S.itt_per(per_b, ref_b), S.itt_per(per_n, ref_n)


def _bg(sd, draw, vals, keys=None):
    """BKS+GOAT's pooled rows (the 40, clean, crunch) and the full summary (all 47 beside)."""
    r = SN.set_rows(sd, draw, vals, keys)
    return {"bks_goat": (r or {}).get("bks_goat") or {}, "pool_47": (r or {}).get("deciding_pool"),
            "per_set": {s: {q: (r or {}).get(s, {}).get(q) for q in ("mean", "lo90", "hi90")}
                        for s in S.SETS} if r else None}


def share(sd, draw, num, den, keys=None):
    """F1's share num/den on the 40 by `fieller_share`, both {pkey: value}."""
    ks = [k for k in num if k in den and num[k] is not None and den[k] is not None and (keys is None or k in keys)]
    den_iv = (_bg(sd, draw, {k: den[k] for k in ks})["bks_goat"] or {}).get("all")

    def iv_of(r):
        return (SN.set_rows(sd, draw, {k: num[k] - r * den[k] for k in ks}) or {}).get("bks_goat", {}).get("all")
    return fieller_share(iv_of, den_iv)


def field_of(per, f="G"):
    return {k: (v or {}).get(f) for k, v in per.items() if v is not None and v.get(f) is not None}


def cmd_gate(_args):
    """G1 (zero renders), once, after stage 1's scores: `xn-bank`'s G and D_swap on the 40 (intent-to-treat, S1),
    `gate`; beside, the realism comparison (the share of `xn-bank`'s gain that `xn-swap` keeps, beside the share real
    build 2 keeps over row (b), both by `fieller_share`), the passing-only read, the refusals and T1's coverage.
    -> gate.json. A holding G1 opens stage 2."""
    m = require_exact(PHASE_TARGETS, *(answers_key(r) for r in STAGES[1]))
    NT.never_overwrite(gate_path())
    from learn import pipeline_fix as P

    draw, sd = context()
    rn = {r: row_numbers(m, draw, r) for r in STAGES[1]}
    gb, gs = field_of(rn["xn-bank"]["itt"]), field_of(rn["xn-swap"]["itt"])
    d_swap = paired(rn["xn-swap"]["itt"], rn["xn-bank"]["itt"])
    rows = {"G_xn-bank": _bg(sd, draw, gb), "G_xn-swap": _bg(sd, draw, gs), "D_swap": _bg(sd, draw, d_swap)}
    g = gate(rows["G_xn-bank"]["bks_goat"].get("all"), rows["D_swap"]["bks_goat"].get("all"))
    real_b, real_n = real_numbers(m, draw, sd)
    beside = {"share_swap_of_bank": share(sd, draw, gs, gb),
              "share_real_b2_of_row_b": share(sd, draw, field_of(real_n), field_of(real_b)),
              "shrunk": {"G_xn-bank": _bg(sd, draw, field_of(rn["xn-bank"]["itt"], "G_shrunk")),
                         "D_swap": _bg(sd, draw, paired(rn["xn-swap"]["itt"], rn["xn-bank"]["itt"], "G_shrunk"))}}
    if any(rn[r]["refused"] for r in STAGES[1]):
        beside["passing_only"] = {"G_xn-bank": _bg(sd, draw, field_of(rn["xn-bank"]["per"])),
                                  "D_swap": _bg(sd, draw, paired(rn["xn-swap"]["per"], rn["xn-bank"]["per"]))}
        beside["passing_only"]["gate"] = gate(beside["passing_only"]["G_xn-bank"]["bks_goat"].get("all"),
                                              beside["passing_only"]["D_swap"]["bks_goat"].get("all"))
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    out = {"plan": PLAN, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "renders": 0, "gate": g, "rows": rows,
           "beside": beside,
           "refusals": {r: {"refused": rn[r]["refused"], "report": S.refusal_report(rn[r]["refused"], sets_of, DECIDING),
                            "control_misses": rn[r]["control_misses"], "nonfinite_replaced": rn[r]["replaced"]}
                        for r in STAGES[1]},
           "coverage": {r: rn[r]["coverage"] for r in STAGES[1]},
           "answers_sha256": {r: rn[r]["answers_sha256"] for r in STAGES[1]},
           "next": "stage 2 (xn-reread, xn-list) runs on its own (N1)" if g["holds"] else
                   "G1 fails: XN-insensitive; stop, to the user"}
    P.save(gate_path(), out)
    a, d = rows["G_xn-bank"]["bks_goat"].get("all") or {}, rows["D_swap"]["bks_goat"].get("all") or {}
    print(f"XN GATE {'HOLDS' if g['holds'] else 'FAILS'}: G(xn-bank) on the 40 {a.get('mean')} [{a.get('lo90')}, "
          f"{a.get('hi90')}] -> {g['xn_bank']}; D_swap {d.get('mean')} [{d.get('lo90')}, {d.get('hi90')}]; share kept "
          f"{beside['share_swap_of_bank'].get('estimate')} ({beside['share_swap_of_bank'].get('shape')}), real "
          f"{beside['share_real_b2_of_row_b'].get('estimate')}; sha256 {S.file_sha(gate_path())}")


def cmd_read(_args):
    """The test's read (zero renders), once: per arm on the 40 (answer deciding, shrunk beside) the paired costs D_swap,
    D*, D_list and D_swap - D*, the share D*/D_swap (`fieller_share`), the gain shares (`xn-swap`, `xn-reread` over
    `xn-bank`, beside real build 2 over row (b)), `list_split`, saved to rows.json before XN_TABLE's code; beside: all
    47, clean and crunch, the checkpoints, D* split at the median re-read F, Spearman of D* with the part's real gap
    (build 2 less row (b)), the one-part-per-partner read, the passing-only read and the refusals, T1's coverage.
    -> rows.json, report.json. With G1 failing, XN-insensitive from stage 1 alone."""
    m = require_exact(PHASE_TARGETS, *(answers_key(r) for r in STAGES[1]))
    gr = gate_record()
    if gr is None:
        raise SystemExit("`gate` has not run")
    rows_run = STAGES[1] + (STAGES[2] if gr["gate"]["holds"] else ())
    for r in rows_run:
        if answers_key(r) not in m:
            raise SystemExit(f"main's {LEDGER_ID} entry has no {answers_key(r)}: merge it before running")
    for p_ in (rows_path(), report_path()):
        NT.never_overwrite(p_)
    build = require_xbuild(m)
    tg = require_targets(m)
    from learn import pipeline_fix as P

    draw, sd = context()
    rn = {r: row_numbers(m, draw, r) for r in rows_run}
    real_b, real_n = real_numbers(m, draw, sd)
    partner_of = {k: t["partner"] for k, t in tg["parts"].items()}
    arms, beside = {}, {}
    for arm, f in ARMS.items():
        it = {r: rn[r]["itt"] for r in rows_run}
        d = {"D_swap": paired(it["xn-swap"], it["xn-bank"], f)}
        if gr["gate"]["holds"]:
            d.update({"D_star": paired(it["xn-reread"], it["xn-bank"], f),
                      "D_list": paired(it["xn-list"], it["xn-bank"], f),
                      "D_swap_less_D_star": paired(it["xn-swap"], it["xn-reread"], f),
                      "reading_proper": paired(it["xn-reread"], it["xn-list"], f)})
        g = {r: field_of(it[r], f) for r in rows_run}
        a = {"D": {n: _bg(sd, draw, v) for n, v in d.items()}, "G": {r: _bg(sd, draw, v) for r, v in g.items()}}
        a["shares"] = {"swap_of_bank": share(sd, draw, g["xn-swap"], g["xn-bank"]),
                       "real_b2_of_row_b": share(sd, draw, field_of(real_n, f), field_of(real_b, f))}
        if gr["gate"]["holds"]:
            a["shares"]["D_star_of_D_swap"] = share(sd, draw, d["D_star"], d["D_swap"])
            a["shares"]["reread_of_bank"] = share(sd, draw, g["xn-reread"], g["xn-bank"])
            a["list_split"] = list_split(a["D"]["reading_proper"]["bks_goat"].get("all"),
                                         a["D"]["D_list"]["bks_goat"].get("all"))
            a["readings"] = {n: SN.paired_reading(a["D"][n]["bks_goat"].get("all")) for n in d}
        a["g_readings"] = {r: S.number_reading(a["G"][r]["bks_goat"].get("all")) for r in rows_run}
        arms[arm] = a
        bs = {}
        if gr["gate"]["holds"]:
            ds = d["D_star"]
            f_of = {k: build["parts"][k]["reread_f"]["f"] for k in ds}
            fig = SN.by_figure(ds, f_of)
            fig["rows"] = {h: (_bg(sd, draw, ds, set(fig[h]))["bks_goat"] or {}).get("all") for h in ("lower", "upper")}
            bs["D_star_by_reread_f"] = dict(fig, note=REREAD_F_NOTE)
            gap = paired(real_n, real_b, f)
            bs["D_star_vs_real_gap_spearman"] = SN.spearman([(ds[k], gap[k]) for k in ds if k in gap])
            bs["real_gap"] = _bg(sd, draw, gap)
            bs["checkpoints"] = {cp: {"D_star": _bg(sd, draw, paired(it["xn-reread"], it["xn-bank"], cp)),
                                      "D_swap": _bg(sd, draw, paired(it["xn-swap"], it["xn-bank"], cp))}
                                 for cp in ("G_cp50", "G_cp100", "G_cp200")}
        one = set(one_per_partner(partner_of))
        bs["one_per_partner"] = {"parts": len(one), "D": {n: (_bg(sd, draw, v, one)["bks_goat"] or {}).get("all")
                                                          for n, v in d.items()}}
        beside[arm] = bs
    refused_any = any(rn[r]["refused"] for r in rows_run)
    passing = None
    if refused_any:
        pr = {r: rn[r]["per"] for r in rows_run}
        passing = {"G_xn-bank": _bg(sd, draw, field_of(pr["xn-bank"])),
                   "D_swap": _bg(sd, draw, paired(pr["xn-swap"], pr["xn-bank"]))}
        passing["gate"] = gate(passing["G_xn-bank"]["bks_goat"].get("all"), passing["D_swap"]["bks_goat"].get("all"))
        if gr["gate"]["holds"]:
            passing["D_star"] = _bg(sd, draw, paired(pr["xn-reread"], pr["xn-bank"]))
            passing["D_swap_less_D_star"] = _bg(sd, draw, paired(pr["xn-swap"], pr["xn-reread"]))
    sets_of = {p["pkey"]: p["set"] for p in draw["parts"]}
    out = {"plan": PLAN, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "renders": 0, "rows_read": list(rows_run),
           "gate": gr["gate"], "gate_sha256": S.file_sha(gate_path()),
           "answers_sha256": {r: rn[r]["answers_sha256"] for r in rows_run},
           "refusals": {r: {"refused": rn[r]["refused"], "report": S.refusal_report(rn[r]["refused"], sets_of, DECIDING),
                            "control_misses": rn[r]["control_misses"], "nonfinite_replaced": rn[r]["replaced"]}
                        for r in rows_run},
           "coverage": {r: rn[r]["coverage"] for r in rows_run}}
    rows = {"arms": arms, "beside": beside, "passing_only": passing}
    P.save(rows_path(), dict(out, rows=rows))            # the rows are saved before the code is read
    a = arms["answer"]
    dall = {n: v["bks_goat"].get("all") for n, v in a["D"].items()}
    code = xn_code(gr["gate"]["holds"], dall.get("D_star"), dall.get("D_swap_less_D_star"))
    code_pass = None
    if passing:
        need = [passing["G_xn-bank"]["bks_goat"].get("all"), passing["D_swap"]["bks_goat"].get("all")]
        if gr["gate"]["holds"]:
            need += [passing["D_star"]["bks_goat"].get("all"), passing["D_swap_less_D_star"]["bks_goat"].get("all")]
        code_pass = S.passing_code(lambda: xn_code(passing["gate"]["holds"],
                                                   (passing.get("D_star") or {}).get("bks_goat", {}).get("all"),
                                                   (passing.get("D_swap_less_D_star") or {}).get("bks_goat",
                                                                                                 {}).get("all")),
                                   all(need))
    label = S.refusal_label(code["code"], (code_pass or {}).get("code")) if code_pass else None
    P.save(report_path(), dict(out, rows=rows, xn=code, code=code["code"], xn_passing_only=code_pass, label=label,
                               shrunk_code=xn_code(gr["gate"]["holds"],
                                                   arms["shrunk"]["D"].get("D_star", {}).get("bks_goat", {}).get("all"),
                                                   arms["shrunk"]["D"].get("D_swap_less_D_star", {}).get("bks_goat",
                                                                                                         {}).get("all")),
                               next="to the user with both reads" if label else code["next"]))
    for n, iv in dall.items():
        print(f"{n} on the 40: {iv}")
    sh = a["shares"].get("D_star_of_D_swap") or {}
    print(f"share D*/D_swap {sh.get('estimate')} {sh.get('shape')} {sh.get('segments')}")
    print(f"XN {code['code']}: {code['reading']}. Next: {code['next']}")


COMMANDS = {"build": cmd_build, "score-check": cmd_score_check, "search-check": cmd_search_check,
            "targets": cmd_targets, "floors": cmd_floors, "floors-real": cmd_floors_real, "floor-read": cmd_floor_read,
            "search": cmd_search, "answers": cmd_answers, "score": cmd_score, "gate": cmd_gate, "read": cmd_read}
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
    args = ap.parse_args(argv)
    if args.cmd in NEEDS_ROW and not args.row:
        ap.error(f"{args.cmd} needs --row")
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
