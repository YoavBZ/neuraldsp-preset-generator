"""Amendment 6 of the direct-model plan: a sound-based stop/go gate for step 3
(`docs/direct-model-sound-gate-amendment.md`; the user approved it on 2026-10-22). Development data
only; no held-out data.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    $MAIN     -m learn.direct_sound_gate gate-render --what truth,constant --shard k/3   # before D exists
    $TORCH_PY -m learn.direct_sound_gate gate-predict              # after step 3's `readout` (zero renders, CPU)
    $MAIN     -m learn.direct_sound_gate gate-render --what D,D0 --shard k/3          # after gate-predict
    $MAIN     -m learn.direct_sound_gate gate-report               # GATE OK | GATE STOP | GATE INCOMPLETE
    $MAIN     -m learn.direct_sound_gate gate-override --decision "..." --date YYYY-MM-DD   # amendment 7

**The set.** R_in: V_sep's examples with their mix and xlance_g stem built and unrefused, Bannockburn
(and every MUSDB18-tagged section) left out, as step 3's `readout` reads it: 1,407 examples, 4 bands.

**Per example**, through the example's own DI section (part C's measured 10-s section, the guitar
alone: no separation, no backing), the same amp and S: the truth (part C's label settings; its render
must reproduce part C's stored guitar mels within one 0.5-dB step on 99% of cells), the constant's
answer, D's answer and (descriptive) D0's. Every answer is S with the labelled dimensions replaced
(`direct_stems.settings_from`), as the truth is.
- **The constant:** per (amp, base class), amendment 5's medians of D's training labels over the
  audible labels (continuous); switches and mics by the same labels' majority and mode.
- **D and D0:** amendment 5's declared answer (A1 mixture medians averaged over 3 seeds x 2 halves,
  pulled by step 3's fitted b toward the constant); switches and mics by `direct_existing.ensemble`
  over the 6 seed x half outputs.

**The score:** d_X = `knob_ceiling.judge` (the project's judge: `aligned_distance`, judge v1 as arm A
and knob_ceiling use it) of X's render against the truth's render, lag 0, on halves A (1.0-5.5 s)
and B (5.5-10.0 s) of the 0.25-s-trimmed render. Per example, the mean over its scorable halves of
log(d_D / d_const), each clipped to [-ln 10, +ln 10]. **GATE OK** iff the paired band-clustered 90% t
interval (4 bands, 3 df) lies entirely below 0; else **GATE STOP**.

**Amendment 7 (user, 2026-10-22).** `gate-override` records the user's decision to run step 4
despite a GATE STOP (override.json: the report's sha256, the decision text and date). It refuses
unless report.json exists, is real and reads STOP; `step3_verdict` passes a STOP only through a
record naming the current report, and step 4 labels everything "run under a user override of a
GATE STOP".

**Renders:** isolate=True, the bounded server, one discarded priming render after a process start or
a (DI section, amp) change, whole sections per shard; at most 3 render processes machine-wide
(`local_objective.RENDERS` counts `gate-render`); disk guard 31 GB. The truth renders are kept
(FLAC, 24-bit, with a power-of-two scale) since every arm is judged against them; the other arms'
renders are kept only for a fixed audit sample of 40 examples (seed 20261087).

The pure parts are unit-tested (`tests/test_direct_sound_gate.py`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import random
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import direct_stems as DS  # noqa: E402

AMENDMENT = "amendment 6 (sound gate)"
WHATS = ("truth", "constant", "D", "D0")       # render order within an example
DECIDING = ("D", "constant")                   # log(d_D / d_const)
CLIP = math.log(10.0)                          # a per-half log ratio is clipped to [-ln 10, +ln 10]
JUDGE_LAG = 0                                  # the truth is a render too: same DI, same latency
AUDIT_SEED = 20261087
AUDIT_N = 40
N_SHARDS = 3
R_IN_EXPECT = 1_407                            # V_sep 1,720 less Bannockburn's 313 (none refused, 2026-10-22)
R_IN_BANDS = 4
DISK_GUARD_GB = 31.0
CONST_TOL = 1e-9                               # the gate's constant against step 3's stored one
SEC_PER_RENDER = 1.58


# --- the readout API (amendment 5), with a fallback --------------------------------------------------------

A5_NAMES = ("median_answers", "pull", "cell_b", "table_from_json", "medians_from_json", "step4_pulls", "READOUT_RULE")


def a5_api(mod=DS):
    """Amendment 5's readout functions in `learn.direct_stems`, or None when they are not there (the
    readout before amendment 5: then D's declared answer cannot be read, and `gate-predict` refuses)."""
    if all(hasattr(mod, n) for n in A5_NAMES):
        return mod
    return None


SILENT_GATES = {"cabParameters/rightCabActive": ("cabParameters/rightCabPosition", "cabParameters/rightCabDistance",
                                                 "cabParameters/rightCabMicLevel", "cabParameters/rightMicType")}


def _silent(Y, cont, sw, cat, gates=SILENT_GATES):
    """Amendment 5's silent masks (a fallback copy of `direct_stems.silent_masks` for one example)."""
    import numpy as np

    c, cm, s, sm, k, km = Y
    cm, km = np.array(cm, copy=True), np.array(km, copy=True)
    for switch, gated in gates.items():
        if switch not in sw:
            continue
        j = sw.index(switch)
        if sm[j] > 0 and s[j] < 0.5:
            for name in gated:
                if name in cont:
                    cm[cont.index(name)] = 0
                if name in cat:
                    km[cat.index(name)] = 0
    return c, cm, s, sm, k, km


def encode_audible(label):
    """`song_model.encode` with amendment 5's silent masks: `direct_stems.encode_audible` when it
    exists, else the same rule here."""
    f = getattr(DS, "encode_audible", None)
    if f is not None:
        return f(label)
    from learn import song_model as SM

    return _silent(SM.encode(label), SM.CONT, SM.SW, SM.CAT)


# --- pure: the set, shards, counts -----------------------------------------------------------------------

def r_in(vsep, tag, mixrows, stemrows):
    """R_in: V_sep's untagged examples with an unrefused mix and stem row (step 3's readout).
    -> (rows, pending): pending lists untagged examples still unbuilt (no mix row, or no stem row)."""
    rows, pending = [], []
    for r in vsep:
        i = r["i"]
        if tag.get(i):
            continue
        m, s = mixrows.get(i), stemrows.get(i)
        if m is None or (not m.get("refused") and s is None):
            pending.append(i)
            continue
        if m.get("refused") or s.get("refused"):
            continue
        rows.append(r)
    return rows, pending


def shard_of(rows, n=N_SHARDS):
    """{i: shard}: whole sections per shard (`direct_stems.shard_sections`, deterministic)."""
    sec = DS.shard_sections(rows, n)
    return {r["i"]: sec[r["section"]] for r in rows}


def shard_rows(rows, k, n=N_SHARDS):
    """Shard k's rows in render order ((section, amp, i): one priming render per group)."""
    s = shard_of(rows, n)
    return DS.render_order(r for r in rows if s[r["i"]] == k)


def parse_what(s):
    w = [x.strip() for x in s.split(",") if x.strip()]
    bad = [x for x in w if x not in WHATS]
    if bad or not w or len(set(w)) != len(w):
        raise argparse.ArgumentTypeError(f"--what takes a comma list of {WHATS}")
    return tuple(x for x in WHATS if x in w)


def pass_renders(rows, whats, done=frozenset()):
    """Renders for one pass over rows in render order: one per (example, arm) not done, plus one
    priming render per (section, amp) group that renders anything."""
    groups, n = set(), 0
    for r in rows:
        todo = [w for w in whats if (r["i"], w) not in done]
        if todo:
            n += len(todo)
            groups.add((r["section"], r["amp"]))
    return n + len(groups)


def planned_renders(rows, n=N_SHARDS, passes=(("truth", "constant"), ("D",), ("D0",))):
    """{pass: renders} when each pass runs once per shard; passes as declared (D and D0 may share one)."""
    out = {}
    for p in passes:
        out["+".join(p)] = sum(pass_renders(shard_rows(rows, k, n), p) for k in range(n))
    return out


def audit_ids(ids, seed=AUDIT_SEED, n=AUDIT_N):
    """The fixed audit sample whose constant, D and D0 renders are kept."""
    ids = sorted(ids)
    return set(random.Random(seed).sample(ids, min(n, len(ids))))


def todo_rows(rows, whats, done):
    """[(row, [arms to render])] for rows with anything left (resumable: `done` is {(i, arm)})."""
    out = []
    for r in rows:
        w = [x for x in whats if (r["i"], x) not in done]
        if w:
            out.append((r, w))
    return out


# --- pure: the answers -------------------------------------------------------------------------------------

def constant_answers(rows, encode, n_cont, n_sw, n_cat):
    """The constant per (amp, base): continuous medians (`direct_stems.label_medians` with `encode`),
    switches by the labels' majority (true iff more than half say true) and mics by the most frequent
    (the lowest index on a tie), each over the labels that set them (`encode`'s masks).
    -> {(amp, base): {"cont": [n] (NaN unset), "sw": [n_sw] bool or None, "mics": [n_cat] int or None}}."""
    import numpy as np

    med = DS.label_medians(rows, encode)
    by = {}
    for r in rows:
        _, _, s, sm, k, km = encode(r["label"])
        by.setdefault((r["amp"], r["base"]), []).append((np.asarray(s), np.asarray(sm), np.asarray(k), np.asarray(km)))
    out = {}
    for cell, v in by.items():
        S = np.stack([x[0] for x in v])
        SM_ = np.stack([x[1] for x in v]) > 0
        K = np.stack([x[2] for x in v])
        KM = np.stack([x[3] for x in v]) > 0
        sw = [None if not SM_[:, j].any() else bool(np.mean(S[SM_[:, j], j]) > 0.5) for j in range(n_sw)]
        mics = []
        for j in range(n_cat):
            if not KM[:, j].any():
                mics.append(None)
                continue
            cnt = np.bincount(K[KM[:, j], j].astype(int))
            mics.append(int(np.argmax(cnt)))
        out[cell] = {"cont": np.asarray(med[cell], np.float64), "sw": sw, "mics": mics}
    assert all(len(out[c]["cont"]) == n_cont for c in out)
    return out


def complete(cont, sw, mics, cm, swm, km):
    """Check an answer covers the labelled dims (masks of the cell's space) and give settings_from's
    inputs: unset dims outside the space read 0 / False / 0 (settings_from ignores them)."""
    import numpy as np

    cont = np.asarray(cont, np.float64)
    if (np.asarray(cm, bool) & ~np.isfinite(cont)).any():
        raise SystemExit("an answer has no value for a labelled continuous dim")
    if any(bool(m) and v is None for m, v in zip(swm, sw)) or any(bool(m) and v is None for m, v in zip(km, mics)):
        raise SystemExit("an answer has no value for a labelled switch or mic")
    return (np.where(np.isfinite(cont), cont, 0.0), [bool(v) if v is not None else False for v in sw],
            [int(v) if v is not None else 0 for v in mics])


def label_answer(label, encode):
    """The label as an answer (cont as float64 from the label itself, not the float32 encoding)."""
    import numpy as np

    from learn import song_model as SM

    _, cm, s, sm, k, km = encode(label)
    cont = np.array([float(label[n]) if n in label else np.nan for n in SM.CONT], np.float64)
    sw = [bool(s[j]) if sm[j] > 0 else None for j in range(len(SM.SW))]
    mics = [int(k[j]) if km[j] > 0 else None for j in range(len(SM.CAT))]
    return cont, sw, mics


def ensemble_votes(outs6):
    """Switches and mics over the 6 seed x half outputs: `direct_existing.ensemble` (a switch is true on
    a strict majority, so a 3-3 tie reads false; mics by the argmax of summed probabilities)."""
    from learn import direct_existing as DE

    _, sw, mics, _ = DE.ensemble([(o[0], o[1], o[3], o[4]) for o in outs6])
    return [bool(x) for x in sw], [int(x) for x in mics]


def model_answers(outs, who, api, table, const, cell_of, mask_of):
    """D's (or D0's) declared answers on R_in (amendment 5): A1 medians averaged over the seeds and the
    example's halves, pulled by the model's fitted b toward the constant; switches and mics by
    `ensemble_votes` over the same outputs. outs: per seed, per row (logpi, mu, ls, sw, [cat]); who: the
    example of each row; mask_of(cell): the cell's labelled continuous dims (`direct_stems.masks`).
    -> {i: {"cont", "a1a2", "sw", "mics", "gaps"}}."""
    import numpy as np

    _, ans = api.median_answers(outs, who)
    rows = {}
    for n, i in enumerate(who):
        rows.setdefault(i, []).append(n)
    out = {}
    for i, ix in rows.items():
        cell = cell_of[i]
        c0 = np.asarray(const[cell], np.float64)
        b, gaps = api.cell_b(table, cell, mask_of(cell))
        cont = api.pull(ans[i], c0, b)
        sw, mics = ensemble_votes([outs[s][n] for s in range(len(outs)) for n in ix])
        out[i] = {"cont": np.asarray(cont, np.float64), "a1a2": np.asarray(ans[i], np.float64), "sw": sw,
                  "mics": mics, "gaps": int(gaps)}
    return out


def same_constant(gate_med, stored_med, cells, tol=CONST_TOL):
    """The gate's continuous constant equals step 3's stored one (amendment 5's readout.json) on the
    cells R_in reads. -> [problems]."""
    import numpy as np

    bad = []
    for cell in sorted(cells):
        a, b = gate_med.get(cell), stored_med.get(cell)
        if a is None or b is None:
            bad.append(f"{cell}: missing")
            continue
        a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
        if a.shape != b.shape or (np.isfinite(a) != np.isfinite(b)).any() or \
                np.nanmax(np.abs(np.where(np.isfinite(a), a - np.where(np.isfinite(b), b, 0), 0)), initial=0) > tol:
            bad.append(f"{cell}: differs")
    return bad


# --- pure: the score and the decision ---------------------------------------------------------------------

def half_logratio(d_x, d_ref, clip=CLIP):
    """log(d_x / d_ref) on one half, clipped to [-clip, +clip]; None when both refused (or both missing).
    A refusal (None or inf: silence) on one side only is the worst for that side; a distance of 0
    reads as the best (both by the clip). -> (value or None, clipped?)."""
    def ok(x):
        return x is not None and math.isfinite(x)

    if not ok(d_x) and not ok(d_ref):
        return None, False
    if not ok(d_x):
        return clip, True
    if not ok(d_ref):
        return -clip, True
    if d_x <= 0 and d_ref <= 0:
        return 0.0, False
    if d_x <= 0:
        return -clip, True
    if d_ref <= 0:
        return clip, True
    v = math.log(d_x / d_ref)
    return max(-clip, min(clip, v)), abs(v) > clip


def example_logratio(j_x, j_ref, clip=CLIP):
    """Per example: the mean over its scorable halves (A, B) of the clipped log ratio.
    j_x, j_ref: {"A": d, "B": d}. -> (value or None, halves scored, halves clipped)."""
    vals, clipped = [], 0
    for h in ("A", "B"):
        v, c = half_logratio((j_x or {}).get(h), (j_ref or {}).get(h), clip)
        if v is not None:
            vals.append(v)
            clipped += int(c)
    return (sum(vals) / len(vals) if vals else None), len(vals), clipped


def paired_logratios(rows_x, rows_ref, ids):
    """{i: per-example log ratio} over ids with both rows, and the counts."""
    out, n_halves, n_clip, unscored = {}, 0, 0, []
    for i in ids:
        if i not in rows_x or i not in rows_ref:
            continue
        v, h, c = example_logratio(rows_x[i].get("judge"), rows_ref[i].get("judge"))
        if v is None:
            unscored.append(i)
            continue
        out[i] = v
        n_halves += h
        n_clip += c
    return out, {"examples": len(out), "halves": n_halves, "clipped_halves": n_clip, "unscored": unscored}


def band_interval(per, band_of):
    """(band-weighted mean, lo, hi, bands): band means, 90% t (`pretrain_set.band_t_interval`)."""
    from learn import pretrain_set as PS

    by = {}
    for i, v in per.items():
        by.setdefault(band_of[i], []).append(v)
    return PS.band_t_interval(by) if by else None


def gate_decision(iv):
    """GATE OK iff the interval lies entirely below 0 (at least 2 bands, finite); else GATE STOP."""
    if iv is None or iv[3] < 2 or not math.isfinite(iv[2]):
        return "STOP"
    return "OK" if iv[2] < 0 else "STOP"


# --- the paths and records ---------------------------------------------------------------------------------

def gate_dir(args):
    return pathlib.Path(args.out).expanduser() if getattr(args, "out", None) else DS.ROOT / "gate"


def build_root(args):
    return pathlib.Path(args.build_root).expanduser() if getattr(args, "build_root", None) else DS.ROOT


def rows_path(gd, what, k, n):
    return gd / "rows" / f"{what}-{k}of{n}.jsonl"


def gate_rows(gd, what):
    """{i: last row} over every shard's JSONL of one arm."""
    out = {}
    for f in sorted((gd / "rows").glob(f"{what}-*.jsonl")):
        for r in DS.read_jsonl(f):
            out[r["i"]] = r
    return out


def truth_path(gd, i):
    return gd / "truth" / f"{int(i) // 1000:04d}" / f"{int(i):07d}.flac"


def audit_path(gd, what, i):
    return gd / "audit" / what / f"{int(i):07d}.flac"


def pow2_scale(y):
    """The smallest power of two at or above the peak (at least 1), so a 24-bit FLAC never clips."""
    import numpy as np

    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    return 1.0 if peak <= 0.999 else float(2.0 ** math.ceil(math.log2(peak / 0.999)))


def write_flac(path, y, sr):
    """y / scale as 24-bit FLAC (atomic). -> (scale, sha256 of the file)."""
    import soundfile as sf

    s = pow2_scale(y)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + f".{os.getpid()}.tmp.flac")
    sf.write(tmp, y / s, sr, subtype="PCM_24", format="FLAC")
    tmp.replace(path)
    return s, DS.hashlib_file(path)


def read_flac(path, scale, sha=None):
    import numpy as np
    import soundfile as sf

    if sha is not None and DS.hashlib_file(path) != sha:
        raise SystemExit(f"{path.name}: hash differs from its row")
    y, _ = sf.read(path, dtype="float64")
    return np.asarray(y, np.float64) * float(scale)


def settings_key(x):
    """A digest of a settings dict {(module, key): stored}."""
    return hashlib.sha1(json.dumps(sorted([list(k), v] for k, v in x.items())).encode()).hexdigest()[:16]


def _jlist(a):
    return [None if (v is None or (isinstance(v, float) and not math.isfinite(v))) else v for v in
            (float(x) if x is not None else None for x in a)]


def _arr(a):
    import numpy as np

    return np.array([np.nan if v is None else v for v in a], np.float64)


def const_json(const):
    return {f"{a}|{b}": {"cont": _jlist(v["cont"]), "sw": v["sw"], "mics": v["mics"]} for (a, b), v in const.items()}


def const_from_json(d):
    return {tuple(k.split("|")): {"cont": _arr(v["cont"]), "sw": v["sw"], "mics": v["mics"]} for k, v in d.items()}


class ShardLock:
    """One process per shard (an exclusive, non-blocking flock); released at exit."""

    def __init__(self, gd, k, n):
        import fcntl

        p = gd / "locks" / f"shard-{k}of{n}.lock"
        p.parent.mkdir(parents=True, exist_ok=True)
        self.fh = open(p, "a")
        try:
            fcntl.flock(self.fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise SystemExit(f"shard {k}/{n} is held by another gate-render process")


# --- the set (needs part C's rows) --------------------------------------------------------------------------

MEM_NEED_GB = 1.5                              # one render process's peak (smoke: 1.5 GB), above the 4 GB floor


def memory_ok(avail, need=MEM_NEED_GB, floor=DS.MEM_FREE_MIN_GB):
    """A render process may load: free memory covers its peak and still leaves the build's 4 GB floor."""
    return avail is None or avail >= floor + need


def wait_memory():
    while not memory_ok(DS.avail_gb()):
        print(f"waiting for memory: {DS.avail_gb():.1f} GB free, need {DS.MEM_FREE_MIN_GB + MEM_NEED_GB:.1f}", flush=True)
        time.sleep(60)


def r_in_problems(ids, answer_ids, readout_n):
    """The gate's R_in against gate-predict's ids and the count step 3's readout read. -> [problems]."""
    bad = []
    if answer_ids is None or sorted(answer_ids) != sorted(ids):
        bad.append("the gate's R_in differs from the examples gate-predict answered")
    if readout_n != len(ids):
        bad.append(f"the gate's R_in has {len(ids)} examples, step 3's readout read {readout_n}")
    return bad


def load_set(broot, stem_sep, quiet=True):
    """(ctx, R_in rows, pending ids) from the build's rows."""
    ctx = DS.Ctx(quiet=quiet)
    mixrows = DS.build_rows(broot, "vsep", "mix")
    stemrows = DS.build_rows(broot, "vsep", stem_sep)
    rows, pending = r_in(ctx.parts["vsep"], ctx.tag, mixrows, stemrows)
    return ctx, rows, pending


def training_rows(ctx, broot, stem_sep, smoke=False):
    """D's training rows (the pool's train examples less the refusals of the mix and stem stages,
    pilot and rest), as step 3 and amendment 5's constant read them. Refuses an incomplete build."""
    mixrows = {**DS.build_rows(broot, "pilot", "mix"), **DS.build_rows(broot, "rest", "mix")}
    stemrows = {**DS.build_rows(broot, "pilot", stem_sep), **DS.build_rows(broot, "rest", stem_sep)}
    unbuilt = DS.full_unbuilt(ctx.pool, mixrows, stemrows, True)
    if unbuilt and not smoke:
        raise SystemExit(f"{len(unbuilt)} pool examples are not built yet: the constant waits for the complete build")
    dropped = DS.refusals(mixrows, stemrows, {r["i"] for r in ctx.pool})
    return [r for r in ctx.pool if not r["early_stop"] and r["i"] not in dropped], sorted(dropped)


def gate_constant(ctx, broot, stem_sep, gd, smoke=False):
    """The constant (computed from the build rows; written once to constant.json, then checked)."""
    from learn import song_model as SM

    rows, dropped = training_rows(ctx, broot, stem_sep, smoke)
    const = constant_answers(rows, encode_audible, len(SM.CONT), len(SM.SW), len(SM.CAT))
    rec = {"amendment": AMENDMENT, "stem_sep": stem_sep, "train_examples": len(rows), "dropped_refused": dropped,
           "smoke": bool(smoke), "constant": const_json(const)}
    p = gd / "constant.json"
    old = DS._load(p)
    if old is not None:
        if old["constant"] != rec["constant"] or old["dropped_refused"] != dropped:
            raise SystemExit("constant.json differs from the constant computed now (the build's refusals changed?)")
    else:
        DS._save(p, rec)
    return const


# --- gate-predict (torch; zero renders) -----------------------------------------------------------------------

def cmd_predict(args):
    """D's and D0's declared answers on R_in (amendment 5, through step 3's readout.json), or (smoke
    only, --label-answers) the labels themselves as a positive control."""
    import numpy as np

    from learn import song_model as SM

    broot, gd = build_root(args), gate_dir(args)
    if (args.smoke or args.limit or args.label_answers) and not args.out:
        raise SystemExit("--smoke, --limit and --label-answers write into a scratch --out only")
    stem_sep = args.sep or DS.STEP_SEP
    ctx, rows, pending = load_set(broot, stem_sep)
    if pending and not args.smoke:
        raise SystemExit(f"{len(pending)} R_in examples are not built")
    rows = rows[:args.limit or None]
    cell_of = {r["i"]: (r["amp"], r["base"]) for r in rows}
    rec = {"amendment": AMENDMENT, "stem_sep": stem_sep, "smoke": bool(args.smoke), "examples": len(rows),
           "r_in_ids": [r["i"] for r in rows],
           "time": time.strftime("%Y-%m-%d %H:%M:%S"), "answers": {}}
    if args.label_answers:
        rec["readout_rule"] = "label (smoke positive control)"
        for name in ("D", "D0"):
            a = {}
            for r in rows:
                cont, sw, mics = label_answer(r["label"], SM.encode)
                a[r["i"]] = {"cont": _jlist(cont), "sw": sw, "mics": mics, "E": 0.0}
            rec["answers"][name] = {str(i): v for i, v in a.items()}
        DS._save(gd / "answers.json", rec)
        print(f"GATE-PREDICT (smoke, label answers): {len(rows)} examples")
        return
    api = a5_api()
    if api is None:
        raise SystemExit("learn.direct_stems has no amendment 5 readout (median_answers, pull, cell_b, ...): "
                         "D's declared answer cannot be read yet")
    import torch

    torch.set_num_threads(2)
    models, D, report, bad = DS.full_models(broot, args.smoke, args.sep)
    stem_sep = DS.step_sep(report, args.sep, args.smoke)
    ro = DS._load(broot / "full" / "readout.json")
    pulls, cmed = DS.step4_pulls(ro, models, args.smoke)
    if not args.smoke and (ro.get("examples") or {}).get("R_in") != len(rows):
        raise SystemExit(f"the gate's R_in has {len(rows)} examples, step 3's readout read {(ro.get('examples') or {}).get('R_in')}")
    rec.update({"readout_rule": api.READOUT_RULE, "D": D, "stem_sep": stem_sep, "parity_problems": bad,
                "readout_sha256": DS.hashlib_file(broot / "full" / "readout.json"),
                "models": {m: {str(r["seed"]): r["model_sha256"] for r in models[m][2]} for m in ("D", "D0")}})
    zarm = {"D": D, "D0": "D0"}
    for name in ("D", "D0"):
        nets = models[name][0]
        outs, who = [[] for _ in nets], []
        for j in range(0, len(rows), 64):
            X, C, Y, w = DS.readout_tensors(broot, rows[j:j + 64], stem_sep, zarm[name])
            o = DS.run_nets(nets, X, C, 32)
            for k in range(len(nets)):
                outs[k] += o[k]
            who += list(w)
            del X, C
        ans = model_answers(outs, who, api, pulls[name], cmed, cell_of, lambda cell: DS.masks(*cell)[0])
        gaps = sum(a["gaps"] for a in ans.values())
        if gaps and not args.smoke:
            raise SystemExit(f"{name}: {gaps} labelled dims have no fitted b")
        out = {}
        for r in rows:
            a = ans[r["i"]]
            c, cm = encode_audible(r["label"])[:2]
            out[str(r["i"])] = {"cont": _jlist(a["cont"]), "a1a2": _jlist(a["a1a2"]), "sw": a["sw"], "mics": a["mics"],
                                "E": DS.ensemble_error(np.where(np.isfinite(a["cont"]), a["cont"], 0.0), c, cm)}
        rec["answers"][name] = out
        print(f"gate-predict {name}: {len(out)} examples", flush=True)
    DS._save(gd / "answers.json", rec)
    print(f"GATE-PREDICT: {len(rows)} examples, D is {D}, {stem_sep} stems, readout {api.READOUT_RULE}")


# --- gate-render ------------------------------------------------------------------------------------------------

def _answer_settings(amp, S, ans, masks):
    cont, sw, mics = complete(_arr(ans["cont"]), ans["sw"], ans["mics"], *masks)
    return DS.settings_from(amp, S, cont, sw, mics)


def cmd_render(args):
    import numpy as np

    from learn import knob_ceiling as K
    from learn import pretrain_set as PS
    from learn import song_bank as B

    broot, gd = build_root(args), gate_dir(args)
    if (args.smoke or args.limit) and not args.out:
        raise SystemExit("--smoke and --limit write into a scratch --out only")
    if not args.smoke and not (PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text().count('"direct-model-sound-gate"'):
        raise SystemExit("the ledger has no direct-model-sound-gate entry")
    k, n = args.shard
    whats = args.what
    stem_sep = args.sep or DS.STEP_SEP
    free = PS.free_gb()
    if free < DISK_GUARD_GB:
        raise SystemExit(f"free disk {free:.1f} GB, below the {DISK_GUARD_GB:.0f} GB guard")
    gd.mkdir(parents=True, exist_ok=True)
    lock = ShardLock(gd, k, n)                                      # noqa: F841 (held until exit)
    DS.wait_render_slot()                                           # before part C's rows (about 1.4 GB) load
    wait_memory()
    ctx, rows, pending = load_set(broot, stem_sep)
    if pending and not args.smoke:
        raise SystemExit(f"{len(pending)} R_in examples are not built ({stem_sep})")
    if len(rows) != R_IN_EXPECT and not args.smoke:
        print(f"note: R_in has {len(rows)} examples, not {R_IN_EXPECT}", flush=True)
    audit = audit_ids([r["i"] for r in rows])
    rows = rows[:args.limit or None]
    mine = shard_rows(rows, k, n)
    done = {(i, w) for w in WHATS for i, r in gate_rows(gd, w).items()}
    truth_rows = gate_rows(gd, "truth")
    const = gate_constant(ctx, broot, stem_sep, gd, args.smoke) if "constant" in whats else None
    sections = ctx.sections
    del ctx                                                         # part C's rows: about 1.4 GB, not needed now
    import gc

    gc.collect()
    answers = None
    if "D" in whats or "D0" in whats:
        answers = DS._load(gd / "answers.json")
        if not answers:
            raise SystemExit("run gate-predict first (answers.json)")
        if answers.get("smoke") and not args.smoke:
            raise SystemExit("answers.json is a smoke test's")
        answers_sha = DS.hashlib_file(gd / "answers.json")
    if "truth" not in whats:
        missing = [r["i"] for r in mine if r["i"] not in truth_rows]
        if missing:
            raise SystemExit(f"{len(missing)} examples of shard {k}/{n} have no truth render: run --what truth first")
    todo = todo_rows(mine, whats, done)
    need = pass_renders(mine, whats, done)
    print(f"gate-render {','.join(whats)} shard {k}/{n}: {len(todo)} examples to do, about {need} renders "
          f"({need * SEC_PER_RENDER / 60:.0f} min)", flush=True)
    if not todo:
        print(f"GATE-RENDER DONE {','.join(whats)} {k}/{n}", flush=True)
        return
    swap0 = DS.swap_mb()
    rr = K.Renderer()
    primer = DS.Primer(rr)
    fhs, checked = {}, set()
    try:
        menu = rr.menu()
        DS.check_recipe(rr)
        for w in whats:
            rp = rows_path(gd, w, k, n)
            rp.parent.mkdir(parents=True, exist_ok=True)
            if rp.exists():
                PS.read_rows(rp, repair=True)
            fhs[w] = open(rp, "a")
        for m, (r, ws) in enumerate(todo):
            g = DS._guards("gate", DISK_GUARD_GB, swap0)
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
            i = r["i"]
            rng, amp, mode, base = PS.plan_example(i)
            if (amp, base) != (r["amp"], r["base"]):
                raise SystemExit(f"{i}: the plan's draw differs from part C's row")
            sel, x, label, _ = PS.settings_for(rng, amp, mode, base, menu, K.START, K.space, K.fmt)
            if {f"{a}/{b}": v for (a, b), v in x.items()} != r["settings"] or label != r["label"]:
                raise SystemExit(f"{i}: settings differ from part C's row")
            S = menu[amp][K.START[base][amp]][1]
            mk = _masks(amp, S)
            if (amp, base) not in checked:                          # gate-predict's masks (the stored menu S)
                if not all(np.array_equal(a, b) for a, b in zip(mk, DS.masks(amp, base))):
                    raise SystemExit(f"{amp} {base}: the plugin's S labels other dims than the stored menu S")
                checked.add((amp, base))
            sec = sections[r["section"]]
            di_full = B.measure(PS.section_audio(sec["path"], sec["start_s"])).astype(np.float32)
            t0_, t1_ = int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR)
            di = np.asarray(di_full, np.float64)[t0_:t1_]
            key = (r["section"], amp)

            def render(xs):
                y = primer.render(key, di_full, sel, xs)
                return (y.mean(axis=1) if y.ndim == 2 else y)[t0_:t1_]

            truth = None
            if "truth" in ws:
                t0 = time.time()
                y = render(x)
                stored = np.load(PS.example_path(i))
                share = min(DS.match_share(mm, stored[f"g{h}"]) for h, mm in PS.halves_mel(y).items())
                row = {"i": i, "what": "truth", "section": r["section"], "band": r["band"], "amp": amp, "base": base,
                       "g_share": share, "settings_key": settings_key(x)}
                if share < DS.MATCH_SHARE:
                    row["refused"] = "the truth render differs from part C's stored mels"
                else:
                    scale, sha = write_flac(truth_path(gd, i), y, PS.SR)
                    row.update(scale=scale, sha256=sha)
                row["seconds"] = round(time.time() - t0, 2)
                fhs["truth"].write(json.dumps(row) + "\n")
                fhs["truth"].flush()
                truth_rows[i] = row
            tr = truth_rows.get(i)
            if tr is None or tr.get("refused"):
                continue
            truth = read_flac(truth_path(gd, i), tr["scale"], tr["sha256"])
            for w in ws:
                if w == "truth":
                    continue
                t0 = time.time()
                if w == "constant":
                    c = const[(amp, base)]
                    xs = _answer_settings(amp, S, {"cont": _jlist(c["cont"]), "sw": c["sw"], "mics": c["mics"]}, mk)
                else:
                    a = answers["answers"][w].get(str(i))
                    if a is None:
                        raise SystemExit(f"{i}: answers.json has no {w} answer")
                    xs = _answer_settings(amp, S, a, mk)
                y = render(xs)
                j = K.judge(truth, y, di, JUDGE_LAG)
                row = {"i": i, "what": w, "band": r["band"], "amp": amp, "base": base,
                       "judge": {h: (v if math.isfinite(v) else None) for h, v in j.items()},
                       "settings_key": settings_key(xs), "same_as_truth": xs == x}
                if w in ("D", "D0"):
                    row["answers_sha256"] = answers_sha
                if i in audit:
                    row["audit_scale"], row["audit_sha256"] = write_flac(audit_path(gd, w, i), y, PS.SR)
                row["seconds"] = round(time.time() - t0, 2)
                fhs[w].write(json.dumps(row) + "\n")
                fhs[w].flush()
            if m % 25 == 0:
                print(f"gate {m + 1}/{len(todo)} i={i} renders {primer.renders} (priming {primer.primes})", flush=True)
    finally:
        for fh in fhs.values():
            fh.close()
        rr.close()
    print(f"GATE-RENDER DONE {','.join(whats)} {k}/{n} (renders {primer.renders}, of them priming {primer.primes})",
          flush=True)


def _masks(amp, S):
    """(continuous, switch, mic) masks of the labelled dims (`knob_ceiling.space` at S)."""
    import numpy as np

    from learn import knob_ceiling as K
    from learn import song_model as SM

    names = {d.name for d in K.space(amp, S)}
    return (np.array([n in names for n in SM.CONT]), np.array([n in names for n in SM.SW]),
            np.array([n in names for n in SM.CAT]))


# --- gate-report ------------------------------------------------------------------------------------------------

def report_table(rows_by_what, ids, band_of, cls_of, amp_of):
    """The deciding contrast and the rows beside it. rows_by_what: {arm: {i: row}}.
    -> dict with 'deciding' (interval), 'decision', counts and descriptive rows."""
    out = {"contrasts": {}, "counts": {}, "by_class": {}, "by_amp": {}, "per_band": {}}
    pairs = [("D", "constant"), ("D0", "constant"), ("D", "D0")]
    per = {}
    for a, b in pairs:
        if a not in rows_by_what or b not in rows_by_what:
            continue
        p, cnt = paired_logratios(rows_by_what[a], rows_by_what[b], ids)
        per[(a, b)] = p
        out["contrasts"][f"{a}-{b}"] = band_interval(p, band_of) if p else None
        out["counts"][f"{a}-{b}"] = {k: (len(v) if isinstance(v, list) else v) for k, v in cnt.items()}
        out["counts"][f"{a}-{b}"]["closer_share"] = (sum(1 for v in p.values() if v < 0) / len(p)) if p else None
        for name, of, dst in (("class", cls_of, out["by_class"]), ("amp", amp_of, out["by_amp"])):
            for g in sorted({of[i] for i in p}):
                sub = {i: v for i, v in p.items() if of[i] == g}
                dst[f"{a}-{b} {g}"] = band_interval(sub, band_of)
        bands = {}
        for i, v in p.items():
            bands.setdefault(band_of[i], []).append(v)
        out["per_band"][f"{a}-{b}"] = {bd: {"mean": sum(v) / len(v), "examples": len(v)} for bd, v in sorted(bands.items())}
    iv = out["contrasts"].get("D-constant")
    out["deciding"] = iv
    out["decision"] = gate_decision(iv)
    return out


def completeness(ids, rows_by_what, needed=("truth", "constant", "D")):
    """-> [problems]: an R_in example without a row for a needed arm (the truth's refusals excepted)."""
    bad = []
    truth = rows_by_what.get("truth", {})
    refused = {i for i, r in truth.items() if r.get("refused")}
    for w in needed:
        rw = rows_by_what.get(w, {})
        miss = [i for i in ids if i not in rw and (w == "truth" or i not in refused)]
        if miss:
            bad.append(f"{w}: {len(miss)} examples have no render row")
    return bad


def cmd_report(args):
    import numpy as np

    broot, gd = build_root(args), gate_dir(args)
    stem_sep = args.sep or DS.STEP_SEP
    ctx, rows, pending = load_set(broot, stem_sep)
    rows = rows[:args.limit or None]
    ids = [r["i"] for r in rows]
    band_of = {r["i"]: r["band"] for r in rows}
    cls_of = {r["i"]: r["base"] for r in rows}
    amp_of = {r["i"]: r["amp"] for r in rows}
    rbw = {w: gate_rows(gd, w) for w in WHATS}
    problems = list(completeness(ids, rbw))
    if pending:
        problems.append(f"{len(pending)} R_in examples are not built")
    answers = DS._load(gd / "answers.json") or {}
    ro = DS._load(broot / "full" / "readout.json") or {}
    if not args.smoke:
        if answers.get("readout_rule") != "amendment 5":
            problems.append(f"D's answers were not read under amendment 5 ({answers.get('readout_rule')})")
        if ro.get("readout_rule") != "amendment 5":
            problems.append("step 3's readout.json is not amendment 5's")
        elif answers.get("models") and {m: ro.get("models", {}).get(m) for m in ("D", "D0")} != answers["models"]:
            problems.append("the answers come from other models than step 3's readout")
        elif answers and answers.get("readout_sha256") != DS.hashlib_file(broot / "full" / "readout.json"):
            problems.append("readout.json changed after gate-predict")
        cj = DS._load(gd / "constant.json")
        if not cj or cj.get("smoke"):
            problems.append("no constant.json (or a smoke test's)")
        elif not ro.get("constant"):
            problems.append("step 3's readout.json stores no constant to check the gate's against")
        else:
            gm = {c: v["cont"] for c, v in const_from_json(cj["constant"]).items()}
            sm = DS.medians_from_json(ro["constant"]) if hasattr(DS, "medians_from_json") else \
                {tuple(k.split("|")): _arr(v) for k, v in ro["constant"].items()}
            problems += [f"constant {p}" for p in same_constant(gm, sm, {(r["amp"], r["base"]) for r in rows})]
    if not args.smoke:
        problems += r_in_problems(ids, answers.get("r_in_ids"), (ro.get("examples") or {}).get("R_in"))
    # every rendered answer is the current one (answers.json unchanged since the render)
    cur = DS.hashlib_file(gd / "answers.json") if (gd / "answers.json").exists() else None
    for w in ("D", "D0"):
        stale = [i for i, r in rbw[w].items() if r.get("answers_sha256") != cur]
        if stale:
            problems.append(f"{w}: {len(stale)} renders were made from another answers.json")
    tab = report_table(rbw, [i for i in ids if not (rbw["truth"].get(i) or {}).get("refused")], band_of, cls_of, amp_of)
    # E (amendment 5, masked) beside it: D's and the constant's on the same examples
    e_rows = {}
    cj = DS._load(gd / "constant.json")
    if answers.get("answers") and cj:
        const = const_from_json(cj["constant"])
        eD, eC, eD0 = {}, {}, {}
        for r in rows:
            i = r["i"]
            c, cm = encode_audible(r["label"])[:2]
            eC[i] = DS.ensemble_error(np.nan_to_num(const[(r["amp"], r["base"])]["cont"]), c, cm)
            for name, dst in (("D", eD), ("D0", eD0)):
                a = answers["answers"].get(name, {}).get(str(i))
                if a is not None:
                    dst[i] = a["E"]
        for name, e in (("D", eD), ("D0", eD0)):
            d = {i: e[i] - eC[i] for i in e if i in eC}
            e_rows[f"E {name}-constant (masked, descriptive)"] = band_interval(d, band_of) if d else None
    counts = {w: len(v) for w, v in rbw.items()}
    renders = sum(1 for w in WHATS for _ in rbw[w].values())
    refused = sum(1 for r in rbw["truth"].values() if r.get("refused"))
    out = {"plan": "docs/direct-model-sound-gate-amendment.md", "amendment": AMENDMENT, "smoke": bool(args.smoke),
           "r_in_examples": len(ids), "rows": counts, "truth_refused": refused, "problems": problems,
           "table": tab, "e_rows": e_rows, "judged_renders_recorded": renders,
           "decision": "INCOMPLETE" if problems else tab["decision"],
           "readout_sha256": answers.get("readout_sha256"), "models": answers.get("models"),
           "rule": "GATE OK iff log(d_D / d_const) per example (mean over halves A and B, each clipped to +-ln 10), "
                   "band-weighted, has a 90% band-clustered t interval (R_in's 4 bands, 3 df) entirely below 0; "
                   "else GATE STOP. E is descriptive.",
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    DS._save(gd / "report.json", out)

    def f(v):
        return "n/a" if v is None else f"{v[0]:+.4f} [{v[1]:+.4f}, {v[2]:+.4f}] ({v[3]} bands)"

    print(f"R_in: {len(ids)} examples; rows {counts}; truth refused {refused}")
    for k, v in tab["contrasts"].items():
        print(f"{'*' if k == 'D-constant' else ' '} log d {k:14s} {f(v)}  {tab['counts'].get(k)}")
    for k, v in {**tab["by_class"], **tab["by_amp"]}.items():
        print(f"  log d {k:22s} {f(v)}")
    for k, v in e_rows.items():
        print(f"  {k:40s} {f(v)}")
    for p in problems:
        print(f"  problem: {p}")
    print(f"GATE {out['decision']}")


def step3_verdict(root=None, gd=None):
    """Step 3's deciding gate for step 4 (amendment 5 as approved: `direct_stems.step3_gate` reads this).
    -> (ok, why): ok for a real GATE OK whose readout.json is the current one, or (amendment 7) for a
    real GATE STOP with a valid user override record (`gate-override`) of that exact report."""
    root = DS.ROOT if root is None else pathlib.Path(root)
    gd = root / "gate" if gd is None else pathlib.Path(gd)
    rep = DS._load(gd / "report.json")
    if not rep:
        return False, "no sound-gate report (run `direct_sound_gate gate-report`)"
    if rep.get("smoke"):
        return False, "the sound-gate report is a smoke test's"
    dec = rep.get("decision")
    if dec not in ("OK", "STOP"):
        return False, f"GATE {dec}"
    ov = None
    if dec == "STOP":
        ov = DS._load(override_path(gd))
        if not ov:
            return False, "GATE STOP"
        bad = override_problem(ov, gd)
        if bad:
            return False, f"GATE STOP; the override record does not apply: {bad}"
    ro = root / "full" / "readout.json"
    if not ro.exists() or rep.get("readout_sha256") != DS.hashlib_file(ro):
        return False, "full/readout.json changed after the sound gate read it"
    if ov:
        return True, f"GATE STOP, {OVERRIDE_LABEL} ({DS.STEP4_OVERRIDE}, user decision {ov['decision_date']})"
    return True, "GATE OK (amendment 6)"


# --- amendment 7: the user's override of a GATE STOP ------------------------------------------------------

OVERRIDE_LABEL = "run under a user override of a GATE STOP"


def override_path(gd):
    return pathlib.Path(gd) / "override.json"


def override_problem(ov, gd):
    """-> None if the override record is amendment 7's and names the current report (sha256), which
    reads a real GATE STOP; else why not."""
    if ov.get("amendment") != DS.STEP4_OVERRIDE:
        return f"not {DS.STEP4_OVERRIDE}'s ({ov.get('amendment')})"
    if ov.get("label") != OVERRIDE_LABEL:
        return "the record carries another label"
    if not (ov.get("user_decision") or "").strip() or not ov.get("decision_date"):
        return "no user decision text or date"
    rp = pathlib.Path(gd) / "report.json"
    if not rp.exists() or ov.get("report_sha256") != DS.hashlib_file(rp):
        return "it was written for another report.json (sha256 differs)"
    if ov.get("report_decision") != "STOP":
        return "it does not override a GATE STOP"
    return None


def override_in_force(root=None, gd=None):
    """The override record when step 3's gate passes through it (amendment 7), else None."""
    root = DS.ROOT if root is None else pathlib.Path(root)
    gd = root / "gate" if gd is None else pathlib.Path(gd)
    rep = DS._load(gd / "report.json") or {}
    if rep.get("decision") != "STOP" or not step3_verdict(root, gd)[0]:
        return None
    return DS._load(override_path(gd))


def override_record(gd, decision, date):
    """Amendment 7's record: the current report must exist, be real and read GATE STOP."""
    rp = pathlib.Path(gd) / "report.json"
    rep = DS._load(rp)
    if not rep:
        raise SystemExit("no sound-gate report (run `gate-report` first)")
    if rep.get("smoke"):
        raise SystemExit("the sound-gate report is a smoke test's")
    if rep.get("decision") != "STOP":
        raise SystemExit(f"the gate reads {rep.get('decision')}: an override is only for a GATE STOP")
    if not (decision or "").strip() or not date:
        raise SystemExit("the override needs the user's decision text and date")
    return {"amendment": DS.STEP4_OVERRIDE, "label": OVERRIDE_LABEL,
            "plan": "docs/direct-model-stems-plan.md, amendment 7",
            "report_sha256": DS.hashlib_file(rp), "report_decision": rep["decision"],
            "report_time": rep.get("time"), "readout_sha256": rep.get("readout_sha256"),
            "deciding_interval": (rep.get("table") or {}).get("deciding"),
            "user_decision": decision.strip(), "decision_date": date,
            "written": time.strftime("%Y-%m-%d %H:%M:%S")}


def cmd_override(args):
    gd = gate_dir(args)
    p = override_path(gd)
    if p.exists():
        raise SystemExit(f"{p} exists (one override per report; remove it by hand only if the user withdraws it)")
    rec = override_record(gd, args.decision, args.date)
    DS._save(p, rec)
    print(f"GATE OVERRIDE ({DS.STEP4_OVERRIDE}): report {rec['report_sha256'][:12]} reads STOP; "
          f"step 4 is {OVERRIDE_LABEL}")


# --- CLI ----------------------------------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(prog="learn.direct_sound_gate")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--out", help="the gate's directory (default ~/ndsp-presets/learn/direct-stems/gate); "
                                     "a scratch directory for smoke tests")
        p.add_argument("--build-root", help="the direct-stems root the build, runs and readout live in (default)")
        p.add_argument("--sep", choices=DS.STEM_SEPS, help="step 3's stems (default xlance_g, amendment 2)")
        p.add_argument("--smoke", action="store_true")
        p.add_argument("--limit", type=int, default=0, help="smoke tests only: the first N R_in examples")

    p = sub.add_parser("gate-render")
    common(p)
    p.add_argument("--what", type=parse_what, required=True, help="comma list of truth, constant, D, D0")
    p.add_argument("--shard", type=DS.parse_shard, default=(0, N_SHARDS))
    p.set_defaults(fn=cmd_render)
    p = sub.add_parser("gate-predict")
    common(p)
    p.add_argument("--label-answers", action="store_true", help="smoke: the labels as D's and D0's answers")
    p.set_defaults(fn=cmd_predict)
    p = sub.add_parser("gate-report")
    common(p)
    p.set_defaults(fn=cmd_report)
    p = sub.add_parser("gate-override", help="amendment 7: record the user's override of a GATE STOP")
    p.add_argument("--out", help="the gate's directory (default ~/ndsp-presets/learn/direct-stems/gate)")
    p.add_argument("--decision", required=True, help="the user's decision, in their words")
    p.add_argument("--date", required=True, help="the date of the user's decision (YYYY-MM-DD)")
    p.set_defaults(fn=cmd_override)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
