"""The rebuild's re-derivation: the diagnosis (Unit 2 of `docs/rederive-plan.md` section 5; ledger `preset-ladder`
`phase_scratch_rederive`, its sha256 into `phase_scratch_rederive_ladder` with the ladder's). Zero renders.

    $MAIN -m learn.rederive_diag run              # xn-list and xf-now against X, per part and per note; D_list read
    $MAIN -m learn.rederive_diag controls         # the bench: per control group, each row's answer from the target
    $MAIN -m learn.rederive_diag controls-real    # fs-refit and build 2 against row (b)'s answers, per control group

`run` (once, after `scratch_rederive ladder`): per part (the 47) it rebuilds three guitars from the ladder's stored
values, each through a recording `Bank` proxy (`RecordingBank`) and a wrapped `note_rebuild.note_end` (`traced`),
with no guarded code changed: X (T, the bank guitar), `xn-list` (today's rule's values from `in-F`) and `xf-now`
(today's rule's values from `in-M`). Each traced guitar must be byte-identical to its untraced composition and to its
stored sha256 (build 2's `tr-di`, the exact-notes build's `xn-list`, the ladder's `xf-now`); a part that fails writes
nothing and the diagnosis is not written. Against X, on the judge's trimmed timeline, per half: the level, the 20-ms
level distribution, J0's pause share and its refusal dry run per frame size (`j0_dry_run`: `aligned_distance`'s
DI-side refusals), envelope correlation, crest and peak, the short-time spectrum (log-mel distance and band levels);
on the whole window the tail decay of isolated onset groups. Per note (`note_table`): its source string and fret, its
end time and kind, its group's level and its level at 0-50 ms and 300-500 ms from the onset. D_list (+0.321
[+0.180, +0.462] on the 40) and its passing-only read (+0.285 [+0.173, +0.396]) are reproduced through
`scratch_notes.set_rows` from the stored score files before any part runs (the run stops when they do not), and every
per-part figure's Spearman with the per-part D_list on the 40 is reported, labelled descriptive. Two sections hold
the design-time parts (`DESIGN_PARTS`): the refused sw50r part (a mutes fault) and GOAT item_69 (a tilt fault).

`controls` (the bench): per answered row (the exact-notes test's four, then the re-derivation's bench rows once their
answers are hashed on main), per control group (`GROUPS`, gate included), how far the row's answer sits from the
part's target (`group_distance`: the mean distance over the group's sounding dims, continuous in unit terms, switches
and categories 0 or 1); beside, each row against `xn-bank`, paired per part. `controls-real`: the answers of
`fs-refit` and build 2 against row (b)'s, per control group, and fs-refit less build 2, paired per part; it refuses
until `fs-refit`'s answers are hashed on main (`phase_scratch_rederive_answers_refit`).

Every command refuses unless this checkout runs main's code (this module and `scratch_rederive`'s pinned files) and
keys, as `scratch_rederive.require_rederive`. Outputs go under `PF/fs/rederive/` only, each file written once; only
group names and aggregates are printed.

The pure parts (`GROUPS`, `control_group`'s mapping, `j0_refusal`, `match_trace`, `note_compare`, `tracker_figures`,
`spearman_table`, `design_parts`, `reproduced`, the guards and the paths) are tested in tests/test_rederive_diag.py on
the light CI runner (no numpy), on synthetic keys; the trace, the figures and the group distances with numpy (skipped
elsewhere).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import pathlib
import statistics
import time

from learn import note_rebuild as NR
from learn import note_transcribe as NT
from learn import scratch_exact as SE
from learn import scratch_rederive as RD
from learn import scratch_search as S

PLAN = RD.PLAN
LEDGER_ID = RD.LEDGER_ID
OWN_FILES = ("learn/rederive_diag.py", "analysis/aligned.py", "learn/knob_ceiling.py", "learn/full_space.py",
             "learn/pipeline_fix.py")   # this module and the four that shape its figures and groups (its own guard)
CODE_FILES = OWN_FILES + tuple(f for f in RD.CODE_FILES if f not in OWN_FILES)
X_NAME = "x"                             # the bank guitar X (T composed), the reference of every figure
DIAG_ROWS = ("xn-list", RD.NOW_ROW)      # the two re-derived guitars traced against X
GUITARS = (X_NAME,) + DIAG_ROWS
VALUES_OF = {X_NAME: None, "xn-list": "in-F", RD.NOW_ROW: RD.DECIDING_INPUT}   # None: T; else today's R from that form
DECLARED = {                             # the stored figures the run must reproduce (docs/rederive-plan.md section 12)
    "d_list": {"mean": 0.321, "lo90": 0.180, "hi90": 0.462},
    "d_list_passing_only": {"mean": 0.285, "lo90": 0.173, "hi90": 0.396},
}
DESIGN_PARTS = ("sw50r-refused", "item_69")   # the refused sw50r part (mutes) and GOAT item_69 (tilt)
GROUPS = ("drive", "tone", "cab", "effects", "gate", "other")   # pipeline_fix.ftg_group's, the gate apart from "other"
ARMS = ("answer", "shrunk")              # the answer decides; shrunk beside
BENCH_ROWS = SE.ROWS + RD.BENCH_ROWS     # the exact-notes test's four, then the re-derivation's
REAL_PAIR = (RD.REAL_ROW, "b2")          # controls-real: fs-refit and build 2, each against row (b)
LEVEL_FRAME_S, LEVEL_HOP_S = NR.MUTE_FRAME_S, NR.MUTE_HOP_S   # the 20-ms level distribution (mute_times' frames)
PERCENTILES = (10, 25, 50, 75, 90)
FLOOR_DB = 40.0                          # J0's playing floor (`aligned_distance` di_floor_db)
BANDS_HZ = {"low": (0.0, 500.0), "mid": (500.0, 2000.0), "high": (2000.0, math.inf)}
J0 = {"di_floor_db": 40.0, "tail_s": 1.5, "min_frames": 8, "max_pauses": 0.5}   # aligned_distance's defaults
DESCRIPTIVE = "descriptive: Spearman with the per-part D_list on the 40 (intent-to-treat); it decides nothing"


# --- the guards and the paths ---------------------------------------------------------------------------------------------

def pinned_identity():
    """OWN_FILES each equal to origin/main's (git diff --quiet); scratch_rederive's own files are its guard's."""
    return {f: SE._git("diff", "--quiet", "origin/main", "--", f).returncode == 0 for f in OWN_FILES}


def require_diag(*phases):
    """Refuse unless `scratch_rederive.require_rederive(*phases)` holds and this module equals main's.
    -> main's entry."""
    m = RD.require_rederive(*phases)
    bad = [f for f, ok in pinned_identity().items() if not ok]
    if bad:
        raise SystemExit(f"this checkout's {bad} differ from main's: run from merged code")
    return m


def diag_dir():
    return RD.rederive_dir() / "diag"


def run_part_path(pk):
    return diag_dir() / "run" / f"{SE._f(pk)}.json"


def run_path():
    return RD.rederive_dir() / "diagnosis.json"


def controls_path(row):
    if row not in BENCH_ROWS:
        raise ValueError(row)
    return diag_dir() / "controls" / f"{row}.json"


def controls_real_path():
    return diag_dir() / "controls-real.json"


# --- the pure parts ---------------------------------------------------------------------------------------------------------

def reproduced(iv, want, places=3):
    """(Pure.) An interval reproduces a declared one when its mean and both ends round to the same `places`."""
    if not RD.iv_ok(iv):
        return False
    return all(round(float(iv[k]), places) == round(float(want[k]), places) for k in ("mean", "lo90", "hi90"))


def group_of_name(name, ftg):
    """(Pure.) A control's group: `ftg` (pipeline_fix.ftg_group) with the gate keys taken out of "other"."""
    if name.startswith("parameters/gate"):
        return "gate"
    g = ftg(name)
    return g if g in GROUPS else "other"


def j0_refusal(playing, pauses, min_frames=J0["min_frames"], max_pauses=J0["max_pauses"]):
    """(Pure.) `aligned_distance`'s DI-side refusal for one frame size, in its order, worded as it words it, or None."""
    if playing < min_frames:
        return "the DI plays in too few frames"
    if pauses > max_pauses:
        return f"{pauses:.0%} of the scored frames are pauses, over {max_pauses:.0%}"
    return None


def placement_order(notes, groups):
    """(Pure.) `synthesise_redo`'s placing order: onset groups in turn, each group's notes by (pitch, index)."""
    return [k for g in groups for k in sorted(g, key=lambda q: (notes[q]["pitch"], q))]


def match_trace(notes, groups, calls, ends, pitch_of):
    """(Pure.) The trace mapped to the notes. `synthesise_redo` places every note first (each `bank.note` call followed
    by one `note_end` call), then renders the placed notes in index order (one `note_end` call each). calls: the bank's
    [(string, fret, cents, samples)]; ends: the note_end calls [{on, off, end, kind, fade}] in call order;
    pitch_of(call) -> the call's pitch. -> {note index: {string, fret, cents, samples, end, kind, fade}}; refuses
    (ValueError) a trace that does not fit."""
    p = len(calls)
    if len(ends) != 2 * p:
        raise ValueError(f"{len(ends)} note_end calls for {p} placed notes: the trace does not fit")
    order = placement_order(notes, groups)
    src, j = {}, 0
    for c, e in zip(calls, ends[:p]):
        while j < len(order) and not (notes[order[j]]["on"] == e["on"] and notes[order[j]]["off"] == e["off"]
                                      and notes[order[j]]["pitch"] == pitch_of(c)):
            j += 1
        if j == len(order):
            raise ValueError("a placement call matches no note in the placing order")
        src[order[j]] = c
        j += 1
    out = {}
    for k, e in zip(sorted(src), ends[p:]):
        if (notes[k]["on"], notes[k]["off"]) != (e["on"], e["off"]):
            raise ValueError(f"note {k}: its render call is not its own")
        s, f, cents, samples = src[k]
        out[k] = {"string": s, "fret": f, "cents": cents, "samples": samples, "end": e["end"], "kind": e["kind"],
                  "fade": e["fade"]}
    return out


def _med(xs):
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    return statistics.median(xs) if xs else None


def _mean(xs):
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    return statistics.fmean(xs) if xs else None


def note_compare(x_rows, y_rows):
    """(Pure.) One guitar's notes against X's, note by note (the same note list). rows: [{played, string, fret, end,
    kind, group_level_db, early_db, late_db}]. -> the per-part aggregates."""
    if len(x_rows) != len(y_rows):
        raise ValueError("the two note tables hold different notes")
    both = [(a, b) for a, b in zip(x_rows, y_rows) if a["played"] and b["played"]]
    kinds = {}
    for a, b in both:
        if a["kind"] != b["kind"]:
            t = f"{a['kind']}->{b['kind']}"
            kinds[t] = kinds.get(t, 0) + 1

    def d(a, b, f):
        return None if a.get(f) is None or b.get(f) is None else b[f] - a[f]
    decay = [None if None in (a["early_db"], a["late_db"], b["early_db"], b["late_db"]) else
             (b["late_db"] - b["early_db"]) - (a["late_db"] - a["early_db"]) for a, b in both]
    n = len(both)
    return {"notes": len(x_rows), "played_x": sum(r["played"] for r in x_rows),
            "played": sum(r["played"] for r in y_rows), "both": n,
            "source_changed": sum((a["string"], a["fret"]) != (b["string"], b["fret"]) for a, b in both),
            "kind_changed": sum(a["kind"] != b["kind"] for a, b in both), "kind_changes": dict(sorted(kinds.items())),
            "end_shift_abs_median_s": _med([abs(b["end"] - a["end"]) for a, b in both]),
            "end_shift_median_s": _med([b["end"] - a["end"] for a, b in both]),
            "group_level_abs_median_db": _med([abs(x) for x in (d(a, b, "group_level_db") for a, b in both)
                                               if x is not None]),
            "early_median_db": _med([d(a, b, "early_db") for a, b in both]),
            "late_median_db": _med([d(a, b, "late_db") for a, b in both]),
            "decay_median_db": _med(decay),
            "source_changed_share": None if not n else sum((a["string"], a["fret"]) != (b["string"], b["fret"])
                                                           for a, b in both) / n,
            "kind_changed_share": None if not n else sum(a["kind"] != b["kind"] for a, b in both) / n}


def tracker_figures(rec, row):
    """(Pure.) One part's flat figures for a traced row (each read against X), the Spearman table's inputs."""
    g = rec["guitars"][row]
    fx = g["figures"]
    nc = g["notes"]
    err = rec["errors"][row]
    groups = max(1, rec["groups"])
    jx = rec["guitars"][X_NAME]["j0"]
    jy = g["j0"]
    pause_up = [jy[h][n]["pauses"] - jx[h][n]["pauses"] for h in jy for n in jy[h]]
    out = {"one_minus_env_corr": None if fx["env_corr"] is None else 1.0 - fx["env_corr"],
           "logmel_to_x": fx["logmel"],
           "crest_diff_db_abs": _abs(fx["crest_diff_db"]), "peak_diff_db_abs": _abs(fx["peak_diff_db"]),
           "tail_decay_abs_median_db": _abs(fx["tail_decay"]["diff_median_db"]),
           "pause_share_rise_max": max(pause_up) if pause_up else None,
           "j0_dry_refusals": sum(jy[h][n]["refused"] is not None for h in jy for n in jy[h]),
           "tuning_error_cents": err["tuning_cents"], "tilt_change_abs_db_s": err["tilt_db_s"],
           "level_error_median_db": err["levels_median_db"],
           "mute_changes_per_group": (err["mutes"]["extra"] + err["mutes"]["missed"]) / groups,
           "source_changed_share": nc["source_changed_share"], "end_kind_changed_share": nc["kind_changed_share"],
           "end_shift_abs_median_s": nc["end_shift_abs_median_s"],
           "early_level_abs_median_db": _abs(nc["early_median_db"]),
           "late_level_abs_median_db": _abs(nc["late_median_db"])}
    for h, v in fx["halves"].items():
        out[f"level_diff_db_abs_{h}"] = _abs(v["level_diff_db"])
        out[f"one_minus_env_corr_{h}"] = None if v["env_corr"] is None else 1.0 - v["env_corr"]
        out[f"logmel_to_x_{h}"] = v["logmel"]
    return out


def _abs(x):
    return None if x is None or not math.isfinite(x) else abs(x)


def spearman_table(figs, d_list, keys):
    """(Pure.) Per figure: Spearman's rho with D_list over `keys` (the parts carrying both), labelled descriptive.
    figs: {pkey: {figure: value}}; d_list: {pkey: value}."""
    from learn import scratch_notes as SN

    names = sorted({n for k in keys for n in (figs.get(k) or {})})
    out = {}
    for n in names:
        pairs = [(figs[k][n], d_list[k]) for k in keys if k in figs and k in d_list and figs[k].get(n) is not None
                 and math.isfinite(figs[k][n]) and d_list[k] is not None]
        out[n] = {"rho": SN.spearman(pairs), "parts": len(pairs)}
    return {"label": DESCRIPTIVE, "figures": out}


def design_parts(draw_parts, list_refused):
    """(Pure.) The two design-time parts' keys: the sw50r part refused in `xn-list`'s answers and GOAT item_69, each
    exactly one. draw_parts: the draw's parts; list_refused: xn-list's refused keys. -> {label: pkey}."""
    sw = [p["pkey"] for p in draw_parts if p["pkey"] in set(list_refused) and p["amp"] == "sw50r"]
    goat = [p["pkey"] for p in draw_parts if p["set"] == "goat"
            and p["unit"].split("/", 1)[-1].split("@", 1)[0] == "item_69"]
    if len(sw) != 1 or len(goat) != 1:
        raise SystemExit(f"the design-time parts are not one each ({len(sw)} sw50r refused, {len(goat)} item_69)")
    return {DESIGN_PARTS[0]: sw[0], DESIGN_PARTS[1]: goat[0]}


CHANGED_NOTE = ("the ladder's `changed_from_today` compares every form's chain cell with the in-M xf-now guitar "
                "(`identical_to_now`), so in in-F and in-U it counts every part for every rung and means nothing; "
                "here each form's chain cell is compared, by its sha256, with that form's own today's-rule cell "
                "(value cell RRRR). The in-M counts, the proofs and the stored guitars are not affected")


def changed_parts(lrecs, keys):
    """(Pure.) Per input form and chain cell: the parts whose chain-cell guitar differs (sha256) from the same form's
    today's-rule guitar (value cell RRRR), beside the ladder's own count (against in-M's xf-now in every form).
    lrecs: {pkey: the ladder's part record}. -> {form: {element: {changed, ladder_reported}}, note}."""
    out = {}
    for u in RD.INPUTS:
        out[u] = {}
        for e in RD.CHAIN_CELLS:
            mine = sum(lrecs[k]["inputs"][u]["chain"][e]["sha256"] != lrecs[k]["inputs"][u]["value"][RD.TODAY]["sha256"]
                       for k in keys)
            theirs = sum(not lrecs[k]["inputs"][u]["chain"][e]["identical_to_now"] for k in keys)
            out[u][e] = {"changed": mine, "ladder_reported": theirs, "parts": len(keys)}
    return {"forms": out, "note": CHANGED_NOTE}


def summarise(recs, keys, rows=DIAG_ROWS):
    """(Pure.) Over `keys`: per traced row, each figure's mean and median, the parts with a J0 dry-run refusal per half
    (row and X), the traced parts and the byte-identical counts."""
    out = {}
    for row in rows:
        figs = [tracker_figures(recs[k], row) for k in keys]
        names = sorted({n for f in figs for n in f})
        jr = {}
        for h in sorted({h for k in keys for h in recs[k]["guitars"][row]["j0"]}):
            jr[h] = {g: sum(any(v["refused"] for v in recs[k]["guitars"][g]["j0"][h].values()) for k in keys)
                     for g in (X_NAME, row)}
        out[row] = {"parts": len(keys), "figures": {n: {"mean": _mean([f.get(n) for f in figs]),
                                                        "median": _med([f.get(n) for f in figs])} for n in names},
                    "j0_dry_refused_parts": jr,
                    "trace_identical": sum(recs[k]["guitars"][row]["trace"]["identical"] for k in keys)}
    return out


# --- the trace (no guarded code changed) -------------------------------------------------------------------------------

class RecordingBank:
    """A `note_rebuild.Bank` stand-in that records every `note` call (string, fret, cents, samples) and hands
    everything else to the bank unchanged."""

    def __init__(self, bank):
        self._bank = bank
        self.calls = []

    def note(self, s, f, cents):
        y = self._bank.note(s, f, cents)
        self.calls.append((s, f, cents, len(y)))
        return y

    def __getattr__(self, name):
        return getattr(self._bank, name)


@contextlib.contextmanager
def traced(bank):
    """`note_rebuild.note_end` wrapped for the block (each call recorded with its result, then restored), and a
    recording proxy of `bank`. -> (proxy, the note_end calls)."""
    proxy, ends = RecordingBank(bank), []
    orig = NR.note_end

    def wrapped(*a, **kw):
        out = orig(*a, **kw)
        ends.append({"on": a[0], "off": a[1], "end": out[0], "kind": out[1], "fade": out[2]})
        return out
    NR.note_end = wrapped
    try:
        yield proxy, ends
    finally:
        NR.note_end = orig


def call_pitch(bank, tuning):
    """A bank call's pitch: the call's cents are 100 * semitones + tuning - the sample's own cents."""
    def pitch_of(c):
        s, f, cents, _ = c
        return NR.nominal_midi(s, f) + int(round((cents - tuning + bank.own_cents(s, f)) / 100.0))
    return pitch_of


def traced_compose(notes, n, bank, ring, finish, values, loud=None, rate=NR.SR):
    """`scratch_rederive.compose` twice, untraced and traced; the trace mapped to the notes. -> (audio float64,
    {identical, notes: {index: ...}})."""
    plain, _ = RD.compose(notes, n, bank, ring, finish, values, loud, rate)
    with traced(bank) as (proxy, ends):
        y, _ = RD.compose(notes, n, proxy, ring, finish, values, loud, rate)
    same = plain.dtype == y.dtype and plain.shape == y.shape and plain.tobytes() == y.tobytes()
    try:
        m = match_trace(notes, NR.onset_groups(notes), proxy.calls, ends, call_pitch(bank, values["tuning"]))
    except ValueError as e:
        raise SystemExit(f"the trace does not fit the notes: {e}; a bug, to the user")
    return y, {"identical": bool(same), "notes": m, "bank_calls": len(proxy.calls), "note_end_calls": len(ends)}


# --- the figures (numpy) ------------------------------------------------------------------------------------------------------

def _lvl(x, t, ab, rate=NR.SR):
    return 20 * math.log10(NR.span_rms(x, int(round((t + ab[0]) * rate)), int(round((t + ab[1]) * rate))) + 1e-12)


def note_table(notes, trace, values, y, rate=NR.SR):
    """Per note: played, its source string and fret, its end time and kind, its group's level (dB) and its level at
    0-50 ms and 300-500 ms from the onset in `y` (the late one None past the window)."""
    gi_of = {k: gi for gi, g in enumerate(NR.onset_groups(notes)) for k in g}
    lv = values["levels"]
    out = []
    for k, nt in enumerate(notes):
        t = trace.get(k)
        on = nt["on"]
        late_ok = (on + NR.TILT_LATE[1]) * rate <= len(y) and on >= 0
        out.append({"played": t is not None, "pitch": nt["pitch"], "on": on,
                    "string": t["string"] if t else None, "fret": t["fret"] if t else None,
                    "end": t["end"] if t else None, "kind": t["kind"] if t else None,
                    "group": gi_of[k], "group_level_db": float(lv[gi_of[k]]) if lv is not None else None,
                    "early_db": _lvl(y, on, NR.TILT_EARLY, rate) if on >= 0 else None,
                    "late_db": _lvl(y, on, NR.TILT_LATE, rate) if late_ok else None})
    return out


def group_decays(notes, x, rate=NR.SR):
    """The level at 300-500 ms less 0-50 ms from the onset of each isolated onset group (`sustain_tilt`'s groups:
    no other onset for 600 ms, the late span inside the window). -> {group index: dB}."""
    groups = NR.onset_groups(notes)
    starts = [notes[g[0]]["on"] for g in groups]
    out = {}
    for gi, t in enumerate(starts):
        nxt = starts[gi + 1] if gi + 1 < len(starts) else math.inf
        if t < 0 or nxt - t < NR.TILT_ISOLATED_S or (t + NR.TILT_LATE[1]) * rate > len(x):
            continue
        out[gi] = _lvl(x, t, NR.TILT_LATE, rate) - _lvl(x, t, NR.TILT_EARLY, rate)
    return out


def j0_dry_run(di_trim, lag, half, n_fft):
    """J0's DI-side read on one half for one frame size, as `aligned_distance` makes it from the DI alone (the dry
    guitar as the judge's DI, `knob_ceiling`'s latency): the playing and scored frames, the pause share
    (`note_transcribe.judge_pause_share`'s) and the refusal it would give (`j0_refusal`), or None."""
    import numpy as np

    from analysis import aligned as A

    from learn import knob_ceiling as K

    di = np.asarray(di_trim, np.float64)
    if not np.any(di):
        return {"playing": 0, "scored": 0, "pauses": 1.0, "refused": "the DI is silent"}
    a, b = K.R.HALVES[half]
    sr, shift = A.SAMPLE_RATE, int(lag)
    start = max(int(a * sr), shift if shift > 0 else 0)
    end = int(b * sr)
    if end - start < sr:
        return {"playing": 0, "scored": 0, "pauses": 1.0, "refused": "under a second to compare once aligned"}
    hop = n_fft // 4
    k = max(1, 1 + (end - start - n_fft) // hop)
    tail = int(round(J0["tail_s"] * sr / hop))
    pre = int(math.ceil(J0["tail_s"] * sr / hop))
    dseg = A._segment(di, start - shift - K.P.LATENCY - pre * hop, end - start + pre * hop)
    playing = A._frame_db(dseg, n_fft) >= A._frame_db(di, n_fft).max() - J0["di_floor_db"]
    scored = A._extend(playing, tail)
    playing, scored = playing[pre:pre + k], scored[pre:pre + k]
    pauses = 1.0 - playing.sum() / scored.sum() if scored.sum() else 1.0
    return {"playing": int(playing.sum()), "scored": int(scored.sum()), "pauses": float(pauses),
            "refused": j0_refusal(int(playing.sum()), float(pauses))}


def j0_table(y_trim, lag=0):
    """`j0_dry_run` per half and frame size. -> {half: {n_fft: ...}}."""
    from analysis import aligned as A

    from learn import knob_ceiling as K

    return {h: {str(n): j0_dry_run(y_trim, lag, h, n) for n in A.FRAME_SIZES} for h in K.R.HALVES}


def _db(x):
    import numpy as np

    r = float(np.sqrt(np.mean(np.asarray(x, np.float64) ** 2))) if len(x) else 0.0
    return 20 * math.log10(r) if r > 0 else None


def _peak_db(x):
    import numpy as np

    p = float(np.abs(x).max()) if len(x) else 0.0
    return 20 * math.log10(p) if p > 0 else None


def _sub(a, b):
    return None if a is None or b is None or not (math.isfinite(a) and math.isfinite(b)) else a - b


def level_distribution(x, rate=NR.SR, top=None):
    """The 20-ms frame levels (5-ms hop, `mute_times`' frames): their percentiles (dBFS) and the share of frames more
    than FLOOR_DB under `top` (the loudest frame of the whole trimmed window by default)."""
    import numpy as np

    L = NR.frame_levels_db(x, int(round(LEVEL_FRAME_S * rate)), int(round(LEVEL_HOP_S * rate)))
    if not len(L):
        return {"frames": 0, "percentiles": {str(p): None for p in PERCENTILES}, "under_floor_share": None}
    t = float(L.max()) if top is None else top
    return {"frames": int(len(L)), "percentiles": {str(p): float(np.percentile(L, p)) for p in PERCENTILES},
            "under_floor_share": float(np.mean(L < t - FLOOR_DB))}


def band_levels(ref, y, rate=NR.SR):
    """The short-time spectrum's band balance: J0's 2,048-sample log-mel frames where `ref` plays (within FLOOR_DB of
    its loudest), each side loudness-free (its mean removed), y less ref per band, averaged in BANDS_HZ."""
    import numpy as np

    from analysis import aligned as A

    k = min(len(ref), len(y))
    R, centres = A._logmel(ref[:k], 2048, rate)
    Y, _ = A._logmel(y[:k], 2048, rate)
    fr = A._frame_db(ref[:k], 2048)
    m = min(len(R), len(Y), len(fr))
    play = fr[:m] >= fr[:m].max() - FLOOR_DB
    if play.sum() < 1:
        return {b: None for b in BANDS_HZ}
    R, Y = R[:m][play], Y[:m][play]
    D = (Y - Y.mean()) - (R - R.mean())
    per = D.mean(axis=0)
    return {b: (float(per[(centres >= lo) & (centres < hi)].mean()) if ((centres >= lo) & (centres < hi)).any()
                else None) for b, (lo, hi) in BANDS_HZ.items()}


def guitar_figures(X, y, notes, trim, rate=NR.SR):
    """One guitar against X (both float64, the section's timeline): whole-window envelope correlation, log-mel
    distance, crest and peak; per half of the judge's trimmed timeline the level, the 20-ms level distribution,
    envelope correlation, log-mel distance, band levels, crest and peak; the tail decay of isolated groups."""
    import numpy as np

    from learn import knob_ceiling as K

    lo, hi = trim
    xt, yt = X[lo:hi], y[lo:hi]

    def nanless(v):
        return None if v is None or not math.isfinite(v) else float(v)
    halves = {}
    Lx = NR.frame_levels_db(xt, int(round(LEVEL_FRAME_S * rate)), int(round(LEVEL_HOP_S * rate)))
    Ly = NR.frame_levels_db(yt, int(round(LEVEL_FRAME_S * rate)), int(round(LEVEL_HOP_S * rate)))
    tx = float(Lx.max()) if len(Lx) else None
    ty = float(Ly.max()) if len(Ly) else None
    for h, (a, b) in K.R.HALVES.items():
        sl = slice(int(a * rate), int(b * rate))
        xh, yh = xt[sl], yt[sl]
        if min(len(xh), len(yh)) < rate:                 # under a second of the half inside the window: not read
            halves[h] = {"samples": int(min(len(xh), len(yh))), "level_diff_db": None, "env_corr": None,
                         "logmel": None}
            continue
        dx, dy = level_distribution(xh, rate, tx), level_distribution(yh, rate, ty)
        halves[h] = {"samples": int(len(xh)), "level_x_db": _db(xh), "level_db": _db(yh),
                     "level_diff_db": _sub(_db(yh), _db(xh)), "levels_x": dx, "levels": dy,
                     "levels_diff_db": {p: _sub(dy["percentiles"][p], v) for p, v in dx["percentiles"].items()},
                     "env_corr": nanless(NR.envelope_corr(xh, yh)),
                     "logmel": nanless(NR.logmel_distance(xh, yh, rate)), "bands_db": band_levels(xh, yh, rate),
                     "crest_diff_db": _sub(nanless(NR.crest_db(yh)), nanless(NR.crest_db(xh))),
                     "peak_diff_db": _sub(_peak_db(yh), _peak_db(xh))}
    dx, dy = group_decays(notes, X, rate), group_decays(notes, y, rate)
    diffs = [dy[g] - dx[g] for g in dx if g in dy]
    return {"env_corr": nanless(NR.envelope_corr(X, y)), "logmel": nanless(NR.logmel_distance(X, y, rate)),
            "crest_diff_db": _sub(nanless(NR.crest_db(y)), nanless(NR.crest_db(X))),
            "peak_diff_db": _sub(_peak_db(y), _peak_db(X)), "halves": halves,
            "tail_decay": {"groups": len(dx), "x_median_db": _med(list(dx.values())),
                           "median_db": _med(list(dy.values())), "diff_median_db": _med(diffs)},
            "identical_to_x": bool(np.array_equal(np.asarray(X, np.float32), np.asarray(y, np.float32)))}


# --- the D_list read (zero renders, the stored score files) -------------------------------------------------------------

def d_list_read(m, draw, sd):
    """D_list = G(xn-list) - G(xn-bank) per part, intent-to-treat (a refused part at Cen, as the exact-notes read) and
    passing-only, from the hashed answers and the stored score files (`scratch_exact.row_numbers`), through
    `scratch_notes.set_rows` (`scratch_exact._bg`). -> {d_list, d_list_passing_only: rows; per-part values;
    reproduced}."""
    rn = {r: SE.row_numbers(m, draw, r) for r in ("xn-bank", "xn-list")}
    itt = SE.paired(rn["xn-list"]["itt"], rn["xn-bank"]["itt"])
    passing = SE.paired(rn["xn-list"]["per"], rn["xn-bank"]["per"])
    rows = {"d_list": SE._bg(sd, draw, itt), "d_list_passing_only": SE._bg(sd, draw, passing)}
    ivs = {k: (v["bks_goat"] or {}).get("all") for k, v in rows.items()}
    stored = None
    if SE.rows_path().exists():
        st = json.loads(SE.rows_path().read_text())
        stored = st["rows"]["arms"]["answer"]["D"]["D_list"]["bks_goat"].get("all") == ivs["d_list"]
    return {"equals_stored_rows": stored, "rows": rows, "intervals": ivs, "per_part": itt, "per_part_passing": passing,
            "refused": sorted(rn["xn-list"]["refused"]),
            "answers_sha256": {r: rn[r]["answers_sha256"] for r in rn},
            "reproduced": {k: reproduced(ivs[k], DECLARED[k]) for k in DECLARED}}


# --- run (zero renders) -----------------------------------------------------------------------------------------------------

def require_ladder(b2_sha, xb_sha):
    """ladder.json with its proofs held on every part, made from these builds; each part record its recorded sha256.
    -> (ladder, {pkey: record})."""
    p = RD.ladder_path()
    if not p.exists():
        raise SystemExit("no ladder.json (run `scratch_rederive ladder` first)")
    lad = json.loads(p.read_text())
    if not lad.get("proofs_hold") or any(v["held"] != v["of"] for v in lad["proofs"].values()):
        raise SystemExit("ladder.json's proofs did not hold on every part")
    if (lad["bank_build_sha256"], lad["exact_build_sha256"]) != (b2_sha, xb_sha):
        raise SystemExit("ladder.json was not made from these builds")
    recs = {}
    for k, r in lad["parts"].items():
        if S.file_sha(RD.part_path(k)) != r["record_sha256"]:
            raise SystemExit("a ladder part record changed since ladder.json")
        recs[k] = json.loads(RD.part_path(k).read_text())
    return lad, recs


def part_diagnosis(key, info, lrec, X32, exact, n, bank, ring, finish, loud, want):
    """One part: the three traced guitars (X, xn-list, xf-now), each byte-identical to its untraced composition and to
    `want[guitar]` (the stored sha256), their figures against X, the per-note tables and the value errors.
    -> (record, ok)."""
    import numpy as np

    lo_hi = SE._trim()
    X64 = np.asarray(X32, np.float64)
    T = lrec["T"]
    vals = {g: (T if VALUES_OF[g] is None else lrec["inputs"][VALUES_OF[g]]["R"]) for g in GUITARS}
    rec = {"plan": PLAN, "part": key, "set": info["set"], "n": n, "notes": len(exact),
           "groups": len(NR.onset_groups(exact)), "ladder_record_sha256": S.file_sha(RD.part_path(key)),
           "guitars": {}, "errors": {}}
    tables = {}
    ok = True
    for g in GUITARS:
        y, tr = traced_compose(exact, n, bank, ring, finish, vals[g], loud)
        y32 = np.asarray(y, np.float32)
        stored = S.npy_sha(y32) == want[g]
        ok &= tr["identical"] and stored
        y64 = np.asarray(y32, np.float64)
        tables[g] = note_table(exact, tr["notes"], vals[g], y64)
        rec["guitars"][g] = {"trace": {"identical": tr["identical"], "stored_sha256_equal": stored,
                                       "bank_calls": tr["bank_calls"], "note_end_calls": tr["note_end_calls"]},
                             "sha256": S.npy_sha(y32), "values": vals[g],
                             "j0": j0_table(y64[lo_hi[0]:lo_hi[1]]),
                             "end_kinds": _count(t["kind"] for t in tables[g] if t["played"]),
                             "note_table": tables[g]}
        if g != X_NAME:
            rec["guitars"][g]["figures"] = guitar_figures(X64, y64, exact, lo_hi)
            rec["guitars"][g]["notes"] = note_compare(tables[X_NAME], tables[g])
            rec["errors"][g] = RD.value_errors(T, vals[g])
    rec["proofs"] = {g: rec["guitars"][g]["trace"] for g in GUITARS}
    return rec, bool(ok)


def _count(xs):
    out = {}
    for x in xs:
        out[x] = out.get(x, 0) + 1
    return dict(sorted(out.items()))


def design_section(label, rec, lrec, d_itt):
    """A design-time part's section (no key): T and today's values per input form, the ladder's cells' distances to
    X in in-F and in-M, the traced rows' figures, end kinds and J0 dry runs, its D_list."""
    lad = {}
    for u in ("in-F", RD.DECIDING_INPUT):
        r = lrec["inputs"][u]
        lad[u] = {"R": {"tuning": r["R"]["tuning"], "mutes": len(r["R"]["mutes"]), "tilt": r["R"]["tilt"]},
                  "value": {c: {f: r["value"][c][f] for f in ("logmel_to_x", "env_corr_to_x", "identical_to_x")}
                            for c in RD.VALUE_CELLS},
                  "chain": {e: {f: r["chain"][e][f] for f in ("logmel_to_x", "env_corr_to_x", "identical_to_x")}
                            for e in RD.CHAIN_CELLS}}
    T = lrec["T"]
    return {"label": label, "set": rec["set"], "d_list": d_itt,
            "T": {"tuning": T["tuning"], "mutes": len(T["mutes"]), "tilt": T["tilt"]}, "ladder": lad,
            "rows": {g: {"figures": tracker_figures(rec, g), "errors": rec["errors"][g],
                         "end_kinds": rec["guitars"][g]["end_kinds"], "j0": rec["guitars"][g]["j0"]}
                     for g in DIAG_ROWS},
            "x": {"end_kinds": rec["guitars"][X_NAME]["end_kinds"], "j0": rec["guitars"][X_NAME]["j0"]}}


def cmd_run(_args):
    """The diagnosis (zero renders), once: D_list reproduced first (the run stops when it is not); per part the three
    traced guitars and their figures (`part_diagnosis`; a part whose trace or stored hash fails writes nothing);
    the summaries on the 40 and all 47, the Spearman tables, the design-time parts' sections. -> diag/run/<part>.json,
    diagnosis.json (never overwritten)."""
    m = require_diag(SE.answers_key("xn-bank"), SE.answers_key("xn-list"))
    NT.never_overwrite(run_path())
    _, why = NT.redo_on_main()
    if why:
        raise SystemExit(why)
    draw, sd = SE.context()
    dl = d_list_read(m, draw, sd)
    if not all(dl["reproduced"].values()) or dl["equals_stored_rows"] is False:
        raise SystemExit(f"D_list does not reproduce from the stored score files ({dl['intervals']}, stored rows "
                         f"{dl['equals_stored_rows']}): a bug, to the user")
    print(f"RDX D_list reproduced: {dl['intervals']['d_list']}; passing-only {dl['intervals']['d_list_passing_only']}",
          flush=True)
    import numpy as np

    from learn import note_fixes as NF
    from learn import pipeline_fix as P

    b2 = SE.bank_build(m)
    xb = SE.require_xbuild(m)
    lad, lrecs = require_ladder(S.file_sha(NT.build_path(RD.BANK_BUILD)), S.file_sha(SE.build_path()))
    fixes, ring, loud = b2["fixes"], b2["ring_variant"], b2.get("loud_gamma")
    if (lad["fixes"], lad["ring_variant"], lad["loud_gamma"]) != (fixes, ring, loud):
        raise SystemExit("ladder.json was not made with build 2's rule")
    excl, _, _, _ = NT._dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    todo = NT.build_todo(NT.install_pair(NT.load_manifest()), NT.ear_items_file(RD.BANK_BUILD))
    parts = [t for t in todo if t[0] == "part"]
    if sorted(k for _, k, *_ in parts) != sorted(lrecs):
        raise SystemExit("the parts are not the ladder's")
    t0 = time.time()
    recs, failed = {}, []
    for kind, key, info, rec, di, finish in parts:
        pp = run_part_path(key)
        if pp.exists():
            r = json.loads(pp.read_text())
            if r["ladder_record_sha256"] != S.file_sha(RD.part_path(key)):
                raise SystemExit("a diagnosis part record was made from another ladder record")
            recs[key] = r
            continue
        tp = time.time()
        X32 = NT.load_dry(RD.BANK_ARM, key, b2)
        di = np.asarray(di, np.float64)
        notes, _ = NT.timed_notes(rec, di)
        exact, _ = NF.apply_fixes(notes, fixes, di)
        if len(exact) != xb["parts"][key]["notes"] or len(X32) != len(di):
            raise SystemExit("a part's exact note list or length is not the exact-notes build's")
        want = {X_NAME: b2["parts"][key]["arms"][RD.BANK_ARM]["sha256"],
                "xn-list": xb["parts"][key]["guitars"]["xn-list"]["sha256"],
                RD.NOW_ROW: lrecs[key]["files"][RD.NOW_ROW]["audio_sha256"]}
        r, ok = part_diagnosis(key, info, lrecs[key], X32, exact, len(X32), bank, ring, finish, loud, want)
        if not ok:
            failed.append(key)
            print(f"part {len(recs) + len(failed)}: TRACE FAILED {r['proofs']}: nothing written for this part",
                  flush=True)
            continue
        r.update(seconds=round(time.time() - tp, 1), time=time.strftime("%Y-%m-%d %H:%M:%S"))
        NT.never_overwrite(pp)
        P.save(pp, r)
        recs[key] = r
        print(f"part {len(recs)} of {len(parts)}: traced, identical; {r['seconds']} s "
              f"({time.time() - t0:.0f} s in all)", flush=True)
    if failed or len(recs) != len(parts):
        raise SystemExit(f"the trace failed on {len(failed)} part(s): diagnosis.json not written; a bug, to the user")
    keys = sorted(recs)
    deciding = [k for k in keys if recs[k]["set"] in RD.DECIDING]
    figs = {row: {k: tracker_figures(recs[k], row) for k in keys} for row in DIAG_ROWS}
    dsg = design_parts(draw["parts"], dl["refused"])
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {RD.PHASE}", "renders": 0, "label": DESCRIPTIVE,
           "ladder_sha256": S.file_sha(RD.ladder_path()), "bank_build_sha256": lad["bank_build_sha256"],
           "exact_build_sha256": lad["exact_build_sha256"], "d_list": {k: v for k, v in dl.items() if k != "per_part"
                                                                       and k != "per_part_passing"},
           "trace_proofs": {g: sum(recs[k]["proofs"][g]["identical"] and recs[k]["proofs"][g]["stored_sha256_equal"]
                                   for k in keys) for g in GUITARS}, "parts_traced": len(keys),
           "deciding_parts": len(deciding),
           "summary": {"the_40": summarise(recs, deciding), "all_47": summarise(recs, keys)},
           "spearman": {row: spearman_table(figs[row], dl["per_part"], deciding) for row in DIAG_ROWS},
           "changed_parts": {"the_40": changed_parts(lrecs, deciding), "all_47": changed_parts(lrecs, keys)},
           "design_parts": {lab: design_section(lab, recs[k], lrecs[k], dl["per_part"].get(k))
                            for lab, k in dsg.items()},
           "parts": {k: S.file_sha(run_part_path(k)) for k in keys},
           "seconds": round(time.time() - t0, 1), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    NT.never_overwrite(run_path())
    P.save(run_path(), out)
    print(f"RDX TRACE: traced audio byte-identical and its stored hash on {out['trace_proofs']} of {len(keys)} parts")
    ch = out["changed_parts"]["all_47"]["forms"]
    print(f"RDX CHANGED PARTS (all 47; each form's chain cell against its own today's-rule cell, the ladder's count "
          f"beside): { {u: {e: (v['changed'], v['ladder_reported']) for e, v in ch[u].items()} for u in ch} }; "
          f"{CHANGED_NOTE}")
    for row in DIAG_ROWS:
        s = out["summary"]["the_40"][row]["figures"]
        sp = out["spearman"][row]["figures"]
        best = sorted(((v["rho"], n) for n, v in sp.items() if v["rho"] is not None), reverse=True)[:5]
        print(f"  {row} on the 40: logmel to X mean {s['logmel_to_x']['mean']}, 1 - env corr mean "
              f"{s['one_minus_env_corr']['mean']}; J0 dry-run refused parts by half "
              f"{out['summary']['the_40'][row]['j0_dry_refused_parts']}; highest Spearman with D_list ({DESCRIPTIVE}): "
              f"{[(n, round(r, 3)) for r, n in best]}")
    for lab, sec in out["design_parts"].items():
        print(f"  {lab}: D_list {sec['d_list']}; mutes T {sec['T']['mutes']}, in-F "
              f"{sec['ladder']['in-F']['R']['mutes']}, "
              f"in-M {sec['ladder']['in-M']['R']['mutes']}; tilt T {sec['T']['tilt']}, in-F "
              f"{sec['ladder']['in-F']['R']['tilt']}, in-M {sec['ladder']['in-M']['R']['tilt']}; env corr to X "
              f"{ {g: sec['rows'][g]['figures']['one_minus_env_corr'] for g in DIAG_ROWS} } (1 - r)")
    print(f"RDX DIAGNOSIS: {len(keys)} parts, {out['seconds']} s; sha256 {S.file_sha(run_path())} (into the ledger as "
          f"{RD.PHASE_LADDER} with the ladder's)")


# --- controls (zero renders) ------------------------------------------------------------------------------------------------

def control_group(name):
    """A settings key's control group (`pipeline_fix.ftg_group`, the gate apart)."""
    from learn import pipeline_fix as P

    return group_of_name(name, P.ftg_group)


def group_distance(a, b, amp, space=None):
    """How far settings `a` sit from `b` on `amp`, per control group, over the dims that sound in either
    (`full_space.encode`'s masks): continuous dims by |unit difference|, switches and categories 0 (same) or 1.
    `space`: `full_space` (a stand-in only in tests). -> {group: {cont, mean_abs_unit, switches, switches_differ,
    cats, cats_differ, dims, distance}}."""
    if space is None:
        from learn import full_space as space

    def enc(x):
        return space.encode({tuple(k.rsplit("/", 1)): v for k, v in x.items()}, amp)

    ca, cma, sa, sma, ka, kma, _ = enc(a)
    cb, cmb, sb, smb, kb, kmb, _ = enc(b)
    grp = {n: control_group(n) for n in list(space.CONT) + list(space.SW) + list(space.CAT)}
    out = {}
    for g in GROUPS:
        cd = [abs(float(ca[j] - cb[j])) for j, n in enumerate(space.CONT) if grp[n] == g and (cma[j] or cmb[j])]
        sd = [float(sa[j] != sb[j]) for j, n in enumerate(space.SW) if grp[n] == g and (sma[j] or smb[j])]
        kd = [float(ka[j] != kb[j]) for j, n in enumerate(space.CAT) if grp[n] == g and (kma[j] or kmb[j])]
        every = cd + sd + kd
        out[g] = {"cont": len(cd), "mean_abs_unit": _mean(cd), "switches": len(sd), "switches_differ": int(sum(sd)),
                  "cats": len(kd), "cats_differ": int(sum(kd)), "dims": len(every),
                  "distance": statistics.fmean(every) if every else None}
    return out


def per_part_distances(answers, against, amp_of, arm="answer"):
    """{pkey: group_distance(answer, against)} over the parts both hold (a differing select is counted apart).
    answers: an answers file's parts; against: {pkey: settings}. -> (per part, select-differs keys)."""
    out, sel = {}, []
    for k, a in answers.items():
        if k not in against or a.get(arm) is None:
            continue
        tgt = against[k]
        if tgt.get("select") is not None and a.get("select") is not None and tgt["select"] != a["select"]:
            sel.append(k)
            continue
        out[k] = group_distance(a[arm], tgt["settings"], amp_of[k])
    return out, sel


def group_values(per, group, field="distance"):
    """(Pure.) {pkey: a group's figure} over the parts where the group has dims."""
    return {k: v[group][field] for k, v in per.items() if v.get(group, {}).get(field) is not None}


def paired_group(new, old, group, field="distance"):
    """(Pure.) Per part new - old on a group's figure, where both have it."""
    a, b = group_values(new, group, field), group_values(old, group, field)
    return {k: a[k] - b[k] for k in a if k in b}


def group_rows(sd, draw, per):
    """Per group: the per-part distance's BKS+GOAT rows (the 40, clean, crunch) and the pool of 47 (descriptive)."""
    out = {}
    for g in GROUPS:
        v = group_values(per, g)
        out[g] = dict(SE._bg(sd, draw, v) if v else {"bks_goat": None, "pool_47": None, "per_set": None}, parts=len(v))
    return out


def rows_answers_path(row, absent):
    """`rederive_rows.answers_path(row)` (Unit 4). Refuses with `absent` only when the module does not exist in this
    checkout (`importlib.util.find_spec`); any error inside it raises as it is, never hidden behind that message."""
    import importlib
    import importlib.util

    if importlib.util.find_spec("learn.rederive_rows") is None:
        raise SystemExit(absent)
    RR = importlib.import_module("learn.rederive_rows")
    if not callable(getattr(RR, "answers_path", None)):
        raise SystemExit("learn/rederive_rows.py has no answers_path(row): the units' interface differs, to the user")
    return RR.answers_path(row)


def _bench_answers(m, row):
    """A bench row's hashed answers file and its path, or None while its answers are not on main."""
    if row in SE.ROWS:
        if SE.answers_key(row) not in m:
            return None
        return SE.require_answers(m, row), SE.answers_path(row)
    key = RD.answers_key(row)
    if key not in m:
        return None
    path = rows_answers_path(row, f"main holds {key} but this checkout has no learn/rederive_rows.py: merge Unit 4")
    return NT.require_file_hash(m, key, path), path


def cmd_controls(_args):
    """The bench (zero renders): per answered row (its answers hashed on main) without a file yet, per part and control
    group, `group_distance` of the answer (and the shrunk answer, beside) from the part's target; per group the rows on
    the 40 and the 47 and the row against `xn-bank`, paired per part. -> diag/controls/<row>.json, each written once;
    the aggregates printed for every row written."""
    m = require_diag(*(SE.answers_key(r) for r in SE.ROWS))
    from learn import pipeline_fix as P

    draw, sd = SE.context()
    tg = SE.require_targets(m)
    amp_of = {p["pkey"]: p["amp"] for p in draw["parts"]}
    against = {k: {"select": t["select"], "settings": t["target"]} for k, t in tg["parts"].items()}
    base = None
    done, waiting = [], []
    for row in BENCH_ROWS:
        got = _bench_answers(m, row)
        if got is None:
            waiting.append(row)
            continue
        ans, path = got
        cp = controls_path(row)
        if cp.exists():
            r = json.loads(cp.read_text())
            if r["answers_sha256"] != S.file_sha(path):
                raise SystemExit(f"{row}'s controls file was made from other answers")
        else:
            per = {arm: per_part_distances(ans["parts"], against, amp_of, arm) for arm in ARMS}
            r = {"plan": PLAN, "row": row, "renders": 0, "label": "descriptive", "answers_sha256": S.file_sha(path),
                 "targets_sha256": S.file_sha(SE.targets_path()), "groups": list(GROUPS),
                 "per_part": {arm: per[arm][0] for arm in ARMS}, "select_differs": {arm: per[arm][1] for arm in ARMS},
                 "rows": {arm: group_rows(sd, draw, per[arm][0]) for arm in ARMS},
                 "time": time.strftime("%Y-%m-%d %H:%M:%S")}
            NT.never_overwrite(cp)
            P.save(cp, r)
        if row == "xn-bank":
            base = r
        done.append((row, r))
    for row, r in done:
        vs = {}
        if base is not None and row != "xn-bank":
            for g in GROUPS:
                d = paired_group(r["per_part"]["answer"], base["per_part"]["answer"], g)
                vs[g] = (SE._bg(sd, draw, d)["bks_goat"] or {}).get("all") if d else None
        line = {g: (((r["rows"]["answer"][g] or {}).get("bks_goat") or {}).get("all") or {}).get("mean")
                for g in GROUPS}
        print(f"RDC {row}: mean distance from the target on the 40 by group {line}"
              + (f"; less xn-bank's {({g: (v or {}).get('mean') for g, v in vs.items()})}" if vs else ""))
    print(f"RDC: {len(done)} rows read ({', '.join(r for r, _ in done)}); waiting for their answers on main: "
          f"{', '.join(waiting) or 'none'}")


def cmd_controls_real(_args):
    """The bridge (zero renders), once, after `fs-refit`'s answers are hashed on main: per part and control group,
    `group_distance` of `fs-refit`'s answer and of build 2's from row (b)'s (the shrunk answers beside); per group
    their rows on the 40 and the 47, and fs-refit less build 2, paired per part. -> diag/controls-real.json."""
    m = require_diag(RD.answers_key(RD.REAL_ROW), SE.PHASE_B2_ANSWERS)
    NT.never_overwrite(controls_real_path())
    from learn import pipeline_fix as P
    from learn import scratch_notes as SN

    refit_path = rows_answers_path(RD.REAL_ROW, "this checkout has no learn/rederive_rows.py: merge Unit 4 first")
    refit = NT.require_file_hash(m, RD.answers_key(RD.REAL_ROW), refit_path)
    b2 = NT.require_file_hash(m, SE.PHASE_B2_ANSWERS, SN.answers_path(SE.BUILD2))
    rb = S.require_hash(S.phase_answers(SE.STEM_ROW), S.answers_path(SE.STEM_ROW))
    draw, sd = SE.context()
    amp_of = {p["pkey"]: p["amp"] for p in draw["parts"]}
    out = {"plan": PLAN, "renders": 0, "label": "descriptive", "rows": list(REAL_PAIR), "against": SE.STEM_ROW,
           "answers_sha256": {RD.REAL_ROW: S.file_sha(refit_path), "b2": S.file_sha(SN.answers_path(SE.BUILD2)),
                              SE.STEM_ROW: S.file_sha(S.answers_path(SE.STEM_ROW))},
           "groups": list(GROUPS), "arms": {}}
    for arm in ARMS:
        against = {k: {"select": a.get("select"), "settings": a[arm]} for k, a in rb["parts"].items()
                   if a.get(arm) is not None}
        per = {RD.REAL_ROW: per_part_distances(refit["parts"], against, amp_of, arm),
               "b2": per_part_distances(b2["parts"], against, amp_of, arm)}
        diff = {}
        for g in GROUPS:
            d = paired_group(per[RD.REAL_ROW][0], per["b2"][0], g)
            diff[g] = dict(SE._bg(sd, draw, d) if d else {"bks_goat": None, "pool_47": None, "per_set": None},
                           parts=len(d))
        out["arms"][arm] = {"per_part": {r: per[r][0] for r in per}, "select_differs": {r: per[r][1] for r in per},
                            "rows": {r: group_rows(sd, draw, per[r][0]) for r in per}, "refit_less_b2": diff}
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    NT.never_overwrite(controls_real_path())
    P.save(controls_real_path(), out)
    a = out["arms"]["answer"]
    for r in REAL_PAIR:
        print(f"RDC-REAL {r} from row (b) on the 40 by group "
              f"{ {g: ((a['rows'][r][g]['bks_goat'] or {}).get('all') or {}).get('mean') for g in GROUPS} }")
    print(f"RDC-REAL fs-refit less build 2 on the 40 by group "
          f"{ {g: (a['refit_less_b2'][g]['bks_goat'] or {}).get('all') for g in GROUPS} }")
    print(f"RDC-REAL: sha256 {S.file_sha(controls_real_path())}")


COMMANDS = {"run": cmd_run, "controls": cmd_controls, "controls-real": cmd_controls_real}


def main(argv=None):
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    for p_ in (str(root), str(root / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    args = ap.parse_args(argv)
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
