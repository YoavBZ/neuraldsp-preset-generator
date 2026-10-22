"""The song-to-preset routes on real mixes (`docs/real-mix-test-plan.md`; amendment 1 in force: the
direct model D runs regardless of step 3's gate, with step 4's models and readout, labelled like
step 4). Arm A (M) and D run on each part's released mix; their stored unity-sum runs (stage F's
M, step 4's D) on the same directions are the other side of each pair. Development only; effect
sizes with 90% band-clustered intervals, no pass/fail bars.

**Trusted parts only** (the user, 2026-10-22: "use only what we can trust, no dirty tracks"). Every
command takes `--trusted FILE` and refuses to run without it. `inputs` records the file's sha256;
every later command refuses a different file (start a new `--out` for a new list). The file is
either JSON, `{"trusted": [entry, ...], ...}` (other keys are kept as notes) or a bare list, or
plain text with one entry per line (`#` starts a comment). An entry is a label-table slug
(`cambridge-magilla-elecgtr1`: both held halves trusted) or a slug with one held half
(`cambridge-magilla-elecgtr1:B`: only directions judged on half B). Entries outside the plan's 17
parts are allowed (the review's list covers more) and are listed, not used.

    T="--trusted ~/ndsp-presets/learn/real-mix-test/trusted.json"
    .venv/bin/python -m learn.real_mix_test inputs $T                     # zero renders: run set, hashes, checks
    $MSST_PY  -m learn.real_mix_test separate $T [--device mps]           # D's crop-only stems (at most 23), CPU by default
    $TORCH_PY -m learn.real_mix_test rebuild $T                            # C′ checks, the real-mix rebuilds
    $TORCH_PY -m learn.real_mix_test predict $T                            # D's answers, control, damping (zero renders)
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.real_mix_test render $T --shard i/3   # i = 0, 1, 2; renders
    .venv/bin/python -m learn.real_mix_test as-mixed $T                    # zero renders
    .venv/bin/python -m learn.real_mix_test report $T

MSST_PY is ~/ndsp-presets/tools/msst-venv/bin/python, TORCH_PY ~/ndsp-presets/tools/demucs-venv/bin/python.
Outputs go to ~/ndsp-presets/learn/real-mix-test/ (`--out DIR` for a scratch run; `--limit K` keeps
the first K run parts and needs `--out`). `smoke` (scratch `--out` only) renders 5 times on one
group, in one process, and only when no other render process runs.

**Inputs** (`inputs`, zero renders). The stored real-mix 10-s crops and Mega-53 stems
(`~/ndsp-presets/learn/mix-previews/sep/mega53/`) are hashed before first use, and every later
read is hash-checked. Checks (any failure stops): the held-out check on the run set (fail
closed); each crop covered by `alignment.json` and re-derived from its preview file at the
stored offset within 1e-6; the Mega-53 run equal to stage F's (checkpoint, pruned head, CPU at 4
threads, chunking); stage F's S, M and step 4's D stored for every run direction; each stored S
render (kept FLAC) re-judged against today's `reference.wav` within 0.005 of its stored judge (a
cleaned amp track or DI would make the stored unity side stale). A rerun refuses when an ok record's
hashes would change. Logged, zero renders: each stem's
lag against the raw track (±100 ms, gain-fitted, sign free; the mix-previews report's), which
replaces stage F's ±3-sample check against the htdemucs crop.

**M_real** (arm A exactly as stage F; only the stem changes): `rebuild` first hash-checks each part's
C′ network against stage F's `rebuild-log.json` and reproduces one stored unity M rebuild within
1e-6, then rebuilds each real-mix Mega-53 stem (`arm_a_mega53.rebuild_parts`). The rebuild-lag
check: GCC(real rebuild, real stem) must equal the stored GCC(unity rebuild, unity stem) within ±3
samples or the run stops (Passing Ships ElecGtr4, with no coherent guitar in its stem, is logged).
`render` runs `arm_a_mega53.run_direction` per direction (52 search renders through the real
rebuild at lag −52, shrink 0.5, the fallback probe, two judges through the measure DI), the
fallback to S counted.

**D_real** (step 4 exactly; amendment 1): `separate` makes a crop-only stem of each real-mix crop
(mastered, and unmastered where there is one) with step 4's separator (`predictions.json`'s
`stem_sep`: X-LANCE gtr_mss), after re-separating one stored unity crop against step 4's stored
stem (≥ 40 dB, a plumbing check). `predict` loads step 3's models (hashes against step 4's
`predictions.json`) and pull, first reproduces step 4's unity answers (A1+A2 within 1e-5 and every
pulled setting equal; else it stops), then answers on the real stems: the mix gets one gain to the training median and the stem
the same gain, the search half only. Zero-render rows: the damping row (the answer's movement
before and after amendment 5's pull, with the pull weight) and the lag/polarity control (the unity
stem shifted by the part's mix lag, and sign-flipped). Every D output carries step 4's label.

**Renders** (`render`): per (part, amp) group one discarded priming render through the real
rebuild at S, arm A's directions, then D's real-mix (and unmastered) answers through the measure
DI (the DI arm A's judges left primed, same amp; a resumed group primes again). Before any group,
shard 0 re-renders S on 6 groups (`random.Random(20261092)`, a priming render each) within 1e-3 of
the stored judge, or every shard stops; the others wait for it (12 renders, not the plan's 6: each S render
is primed; 5,811 renders on all 17 parts stay under the cap). isolate=True; at most 3 render
processes machine-wide (counted as python jobs and render servers at start); the 31 GB disk guard;
the swap guard; a hard cap of 6,300 renders; resumable by direction (arm A) and render (D).

**Report.** Per direction log(d_real / d_unity) for M and D (the real-mix penalty) and X_real − S,
per part over amps and halves, band-weighted with the 90% band-clustered t interval
(`arm_a_levers.effects`: per amp, per class, part-weighted, leave one band out), on the directions
where S, M and D score on both sides. Beside it, never promoted: the subsets (6 lagged parts, 8
flipped, Colour Me Red x2), D on the unmastered parts, per part against the stem SNR change and D's
input level shift, the damping and control rows, and "as mixed" (`as-mixed`, zero renders): the
target is `reference.wav` carried into the real mix by a lag and a 1/3-octave EQ fitted on each
direction's search half (the cross-correlation's peak, then |Σ S_xy| / Σ S_xx per band), every arm re-judged on the held
half from the kept FLACs at judge_lag + that lag; a part is left out when a fit's mean coherence
over 0.2-5 kHz is below 0.1 (the declared floor: about 5 of 17 parts pass, a thin row), and when only
one held half is trusted (its fit would read the untrusted half); the same fit on the unity mix is the
control. The lag method was chosen on lag agreement with the stems, not on scores (`NOTES`).

The pure parts are unit-tested (`tests/test_real_mix_test.py`); the commands that load audio,
models or the renderer are not, like the other step modules.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import statistics
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import arm_a_mega53 as A  # noqa: E402
from learn import direct_stems as DS  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn import mix_previews as MP  # noqa: E402

L, LO, R = A.L, A.LO, A.R

OUT = K.HOME / "learn/real-mix-test"
MEGA_REAL = MP.OUT / "sep" / "mega53"            # the stored real-mix crops and Mega-53 stems
ALIGNMENT = MP.IN / "alignment.json"
MP_REPORT = MP.OUT / "report.json"
SR, CROP = A.SR, A.CROP
PLAN = "docs/real-mix-test-plan.md (amendment 1)"

# --- the parts (the plan's table) -------------------------------------------------------------------
PARTS = tuple(s for s in A.pool_slugs() if s.startswith("cambridge-"))       # the 17 with a released mix
REMIX = {"cambridge-Signs-ElecGtr3": "remix_mastered"}                       # Sound On Sound's Mix Rescue remix
UNMASTERED = ("cambridge-Passing_Ships-ElecGtr2", "cambridge-Passing_Ships-ElecGtr4", "cambridge-Quicksand-ElecGtr2",
              "cambridge-Signs-ElecGtr3", "cambridge-femme-elecgtr5", "cambridge-get-out-of-bed-elecgtr2")
LAGGED = ("cambridge-Today's_The_Day-ElecGtr07", "cambridge-wickerman-elecgtr1", "cambridge-wickerman-elecgtr2",
          "cambridge-wickerman-elecgtr3", "cambridge-let-s-dance-elecgtr3", "cambridge-let-s-dance-elecgtr4")
FLIPPED = ("cambridge-magilla-elecgtr1", "cambridge-get-out-of-bed-elecgtr2", "cambridge-let-s-dance-elecgtr3",
           "cambridge-let-s-dance-elecgtr4", "cambridge-Quicksand-ElecGtr2", "cambridge-wickerman-elecgtr1",
           "cambridge-wickerman-elecgtr2", "cambridge-wickerman-elecgtr3")
XLANCE_FAILURES = ("cambridge-colour-me-red-elecgtr02", "cambridge-colour-me-red-elecgtr03")
NO_COHERENT_GUITAR = ("cambridge-Passing_Ships-ElecGtr4",)                  # its lag check is logged, not a stop

# --- the checks -------------------------------------------------------------------------------------
REPEAT_SEED = 20261092
REPEAT_N = 6
REPEAT_TOL = 1e-3                                # |log| of S's fresh judge against the stored one
S_FLAC_TOL = A.TOL                               # 0.005: a 16-bit kept FLAC re-judged
IDENTITY_TOL = 1e-6
LAG_TOL = 3                                      # samples
MAX_LAG = 4800                                   # ±100 ms
CROP_TOL = 1e-6
A1A2_TOL = 1e-5                                  # step 4's unity answers reproduced
SEP_REPRO_DB = 40.0                              # one unity crop re-separated against step 4's stored stem
MEGA53_RUN_KEYS = ("model", "stem", "pruned", "threads", "device", "inference")

# --- "as mixed" (declared in the plan) -------------------------------------------------------------
COH_MIN = 0.1
COH_BAND = (200.0, 5000.0)
EQ_RANGE = (50.0, 16000.0)                       # the 1/3-octave centres fitted
EQ_NPERSEG = 4096

# --- renders and the machine ----------------------------------------------------------------------
CAP = 6_300
D_ARMS = ("D_real", "D_unm")
FIXED = ("S", "M_unity", "M_real", "D_unity", "D_real")      # every primary reads this direction set
CONTRASTS = {"M_penalty": ("M_real", "M_unity"), "D_penalty": ("D_real", "D_unity"),
             "M_real_minus_S": ("M_real", "S"), "D_real_minus_S": ("D_real", "S"),
             "M_unity_minus_S": ("M_unity", "S"), "D_unity_minus_S": ("D_unity", "S")}
PRIMARY = ("M_penalty", "D_penalty")
UNM_CONTRASTS = {"D_unmastered_minus_D_unity": ("D_unm", "D_unity"), "D_unmastered_minus_D_real": ("D_unm", "D_real"),
                 "D_unmastered_minus_S": ("D_unm", "S")}
ROWS = ("all", "lagged", "flipped", "xlance_failures")
SEP_MIN_GB = 4.0
REPEAT_WAIT_S = 1800
NOTES = {
    "repeat_check": ("the repeat check uses 12 renders, not the plan's 6: each of its 6 S renders is primed (one "
                     "discarded render after a DI or amp change); 5,811 renders on all 17 parts stay under the 6,300 cap"),
    "as_mixed_lag": ("'as mixed' fits one lag per direction on its search half from the plain cross-correlation; that "
                     "method was chosen on lag agreement with the real-mix stems' logged lags (14 of 17 parts; "
                     "GCC-PHAT locked onto amp-track bleed at lag 0), not on any score"),
    "coherence": ("the 'as mixed' coherence floor stays at the declared 0.1, so the row is thin: on all 17 parts only 5 "
                  "pass (Quicksand 2, femme 5, get-out-of-bed 2, Let's Dance 3 and 4; 4 bands), measured 2026-10-22 "
                  "with zero renders; the unity mixes mostly read below 0.1 too"),
}
POLL_S = 60


def _save(path, obj):
    A._save(path, obj)


def _load(path):
    return A._load(path)


def _pos(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x > 0


# --- the trusted list (pure) ------------------------------------------------------------------------

def parse_trusted(text, name=""):
    """-> [(slug, held half or None)] from the file's text (JSON or one entry per line)."""
    s = text.strip()
    if name.endswith(".json") or s.startswith(("{", "[")):
        try:
            obj = json.loads(s)
        except json.JSONDecodeError as e:
            raise ValueError(f"not valid JSON: {e}") from None
        if isinstance(obj, dict):
            if "trusted" not in obj:
                raise ValueError("a JSON trusted list needs a 'trusted' key")
            obj = obj["trusted"]
        if not isinstance(obj, list) or not all(isinstance(x, str) for x in obj):
            raise ValueError("'trusted' must be a list of strings")
        raw = obj
    else:
        raw = [ln.split("#", 1)[0] for ln in text.splitlines()]
    out = []
    for x in (r.strip() for r in raw):
        if not x:
            continue
        slug, sep, half = x.partition(":")
        if not slug or (sep and half not in ("A", "B")):
            raise ValueError(f"bad entry {x!r}: a slug, or slug:A / slug:B (one held half)")
        out.append((slug, half or None))
    return out


def run_set(entries, parts=PARTS):
    """-> ({slug: [trusted held halves]} for the plan's parts, [entries outside them])."""
    run, outside = {}, set()
    for slug, half in entries:
        if slug not in parts:
            outside.add(slug if half is None else f"{slug}:{half}")
            continue
        run.setdefault(slug, set()).update(("A", "B") if half is None else (half,))
    return {s: sorted(h) for s, h in sorted(run.items())}, sorted(outside)


def read_trusted(path):
    """-> (path, entries, sha256); SystemExit without a readable list."""
    if not path:
        raise SystemExit("--trusted FILE is required: the test runs on trusted parts only (the user's rule, 2026-10-22)")
    p = pathlib.Path(path).expanduser()
    if not p.is_file():
        raise SystemExit(f"trusted list {p} not found: the test runs on trusted parts only")
    try:
        entries = parse_trusted(p.read_text(), p.name)
    except ValueError as e:
        raise SystemExit(f"trusted list {p}: {e}") from None
    return p, entries, LO.file_sha256(p)


# --- the run's directions and counts (pure) ---------------------------------------------------------

def mastered_kind(slug):
    return REMIX.get(slug, "preview_mastered")


def kinds(slug):
    return (mastered_kind(slug),) + (("unmastered",) if slug in UNMASTERED else ())


def run_dirs(run):
    """(slug, amp, search, held) for every run part and amp, the directions whose held half is trusted."""
    return [(s, amp, sh, h) for s in sorted(run) for amp in K.AMPS for sh, h in K.DIRECTIONS if h in run[s]]


def d_arms(slug):
    return ("D_real", "D_unm") if slug in UNMASTERED else ("D_real",)


def repeat_groups(groups, n=REPEAT_N, seed=REPEAT_SEED):
    gs = sorted(map(tuple, groups))
    return sorted(random.Random(seed).sample(gs, min(n, len(gs))))


def expected_renders(dirs):
    """The plan's counts on the run set: one priming render per group, arm A's 55 per direction, D
    once per direction (real mix, and unmastered where there is one), the repeat check (a priming
    render and S on each repeat group)."""
    g = len(A.groups(dirs))
    out = {"priming": g, "arm_A": len(dirs) * A.PER_DIRECTION, "D_real": len(dirs),
           "D_unmastered": sum(1 for d in dirs if d[0] in UNMASTERED), "repeat_check": 2 * min(REPEAT_N, g)}
    out["total"] = sum(out.values())
    return out


# --- paths -------------------------------------------------------------------------------------------

def out_root(args):
    return pathlib.Path(args.out).expanduser() if getattr(args, "out", None) else OUT


def real_crop_path(slug, kind):
    return MEGA_REAL / f"{slug}--{kind}-mix.npy"


def mega_real_path(slug, kind):
    return MEGA_REAL / f"{slug}--{kind}.npy"


def sep_dir(root, sep_name):
    return root / "sep" / sep_name


def xl_path(root, sep_name, slug, kind):
    return sep_dir(root, sep_name) / f"{slug}--{kind}.npy"


def rebuilt_path(root, slug):
    return root / "rebuilt" / f"{slug}.npy"


def m_path(root, slug, amp, search):
    return root / "M" / slug / amp / f"{search}.json"


def group_path(root, slug, amp):
    return root / "groups" / f"{slug}|{amp}.json"


def audio_path(root, slug, amp, arm, search):
    return root / "audio" / slug / amp / f"{arm}-{search}.flac"


def step4_dir():
    return DS.step4_dir(DS.ROOT)


def unity_rebuild_log():
    return _load(A.fdir("rebuilt", "mega53", "rebuild-log.json")) or {}


def load_checked(path, sha):
    import numpy as np

    if LO.file_sha256(path) != sha:
        raise SystemExit(f"{path}: changed since it was recorded")
    return np.load(path)


def state(args):
    """(root, inputs record) after the trusted-list and inputs checks every command but `inputs` needs."""
    root = out_root(args)
    _, _, sha = read_trusted(args.trusted)
    rec = _load(root / "inputs.json")
    if rec is None:
        raise SystemExit(f"run `inputs` first ({root / 'inputs.json'} is missing)")
    if rec["trusted"]["sha256"] != sha:
        raise SystemExit("this trusted list is not the one `inputs` recorded: start a new --out for a new list")
    if not rec.get("ok"):
        raise SystemExit(f"`inputs` found problems: {json.dumps(rec.get('problems'), ensure_ascii=False)[:2000]}")
    return root, rec


# --- checks (pure) -----------------------------------------------------------------------------------

def provenance_problems(real_run, f_run, keys=MEGA53_RUN_KEYS):
    """The real-mix Mega-53 run against stage F's: the same checkpoint and setting."""
    if not real_run or not f_run:
        return ["a Mega-53 run.json is missing"]
    p = [f"{k}: {real_run.get(k)!r} against stage F's {f_run.get(k)!r}" for k in keys if real_run.get(k) != f_run.get(k)]
    a, b = real_run.get("provenance") or {}, f_run.get("provenance") or {}
    if a.get("commit") != b.get("commit") or ([f.get("sha256") for f in a.get("files", [])]
                                               != [f.get("sha256") for f in b.get("files", [])]):
        p.append("provenance (commit or checkpoint hashes) differs")
    return p


def network_problems(slugs, unity_log, path_of, sha_of):
    """Each part's C′ network against stage F's rebuild-log.json: the same file and hash."""
    out = {}
    for s in slugs:
        st = unity_log.get(s)
        if not st:
            out[s] = "not in stage F's rebuild-log.json"
            continue
        p = path_of(s)
        if str(p) != st.get("network"):
            out[s] = f"network {p} is not stage F's {st.get('network')}"
        elif sha_of(p) != st.get("network_sha256"):
            out[s] = "network hash differs from stage F's"
    return out


def used_network_problems(real_log, unity_log, slugs):
    """After the rebuilds: each part was rebuilt by stage F's network (file and hash as logged)."""
    out = {}
    for s in slugs:
        a, b = real_log.get(s) or {}, unity_log.get(s) or {}
        if (a.get("network"), a.get("network_sha256")) != (b.get("network"), b.get("network_sha256")):
            out[s] = f"rebuilt by {a.get('network')} ({a.get('network_sha256')}), stage F by {b.get('network')}"
    return out


def rebuild_lag_problems(real_log, unity_log, slugs, tol=LAG_TOL, logged_only=NO_COHERENT_GUITAR):
    """The plan's rebuild-lag check. -> ({slug: why} that stop the run, {slug: why} logged instead)."""
    stop, logged = {}, {}
    for s in slugs:
        a = (real_log.get(s) or {}).get("gcc_vs_source")
        b = (unity_log.get(s) or {}).get("gcc_vs_source")
        if isinstance(a, int) and isinstance(b, int) and abs(a - b) <= tol:
            continue
        why = f"GCC(real rebuild, real stem) {a} against the stored GCC(unity rebuild, unity stem) {b} (limit ±{tol})"
        (logged if s in logged_only else stop)[s] = why
    return stop, logged


def logged_lag(stem, ref, max_lag=MAX_LAG):
    """The lag that replaces stage F's ±3-sample check: best |xcorr| of the stem against the raw
    track within ±100 ms (`mix_previews.best_lag`: ref[t] ~ stem[t − lag]), and the gain-fitted
    (sign-free) SNR there."""
    from learn import stereo_mix_check as SMC

    lag, r = MP.best_lag(stem, ref, max_lag)
    return {"lag": int(lag), "r": float(r), "snr_db": float(SMC.snr_db(MP.shift(stem, lag), ref))}


def mix_shift(real, unity):
    """The part's mix lag and polarity from the logged lags of its real and unity stems: the delay
    that moves the unity stem onto the real one (`mix_previews.shift(unity stem, delay)`), and
    whether the real mix flips it."""
    return int(unity["lag"] - real["lag"]), (real["r"] < 0) != (unity["r"] < 0)


def stored_problems(dirs, s_done, m_done, d_done, in_log):
    """Stage F's S and M and step 4's D stored for every run direction (the unity side)."""
    out = []
    for s, a in A.groups(dirs):
        if not s_done(s, a):
            out.append(f"stage F S {s} {a}")
        if not d_done(s, a):
            out.append(f"step 4 D group {s} {a}")
    out += [f"stage F M {d[0]} {d[1]} {d[2]}" for d in dirs if not m_done(*d[:3])]
    out += [f"stage F Mega-53 rebuild {s}" for s in sorted({d[0] for d in dirs}) if not in_log(s)]
    return out


def unity_check_ok(per_direction, tol=A1A2_TOL):
    """Step 4's unity answers reproduced: on every direction the A1+A2 answer within `tol` (before the
    pull) and the pulled settings equal to step 4's (so a changed pull in readout.json cannot slip
    through)."""
    return bool(per_direction) and all(v["a1a2_max_abs_diff"] <= tol and v["settings_equal"] is True
                                       for v in per_direction.values())


# --- the machine (pure) -----------------------------------------------------------------------------

def render_blocker(ps, own=(), servers=True):
    """arm_a_mega53's gate (python render jobs, cap 3; 2 beside a separation), and at a process's
    start also the render servers (another session's renderer counts even if its job is not listed)."""
    why = A.render_blocker(ps, own)
    if why or not servers:
        return why
    n = sum(1 for p, c in ps if p not in own and "au_render_server" in c)
    return f"{n} render servers running (cap {A.RENDER_CAP})" if n >= A.RENDER_CAP else None


def mps_users(ps, own=()):
    """Processes that may hold the MPS GPU: training jobs, separations, anything run with --device mps."""
    from learn import ks_extend as X
    from learn import local_objective_1c as C

    out = []
    for p, c in ps:
        if p in own or not X._is_python(c):
            continue
        if C.is_training(c) or A._matches(c, A.SEPARATIONS) or "--device mps" in c or "--device=mps" in c:
            out.append(p)
    return out


def sep_blockers(ps, own, avail_gb, device, min_gb=SEP_MIN_GB):
    """A separation runs only on an idle renderer (the plan): no render job or server, no other
    separation, the memory gate; on MPS also no other MPS user."""
    out = []
    rp = A.render_procs(ps, own)
    srv = [p for p, c in ps if p not in own and "au_render_server" in c]
    if rp or srv:
        out.append(f"the renderer is not idle (jobs {rp}, servers {srv})")
    sp = A.separation_procs(ps, own)
    if sp:
        out.append(f"another separation {sp}")
    if device == "mps":
        mu = mps_users(ps, own)
        if mu:
            out.append(f"MPS may be in use by {mu}")
    if avail_gb is None or avail_gb < min_gb:
        out.append(f"available memory {avail_gb} GB, under {min_gb} GB")
    return out


def _own():
    return {os.getpid(), os.getppid()}


def wait_render_gate(servers=True):
    while True:
        why = render_blocker(A._ps(), _own(), servers)
        if why is None:
            return
        print(time.strftime("%H:%M:%S"), "render gate:", why, flush=True)
        time.sleep(POLL_S)


# --- renders (pure apart from the renderer passed in) -----------------------------------------------

def repeat_check(rr, items, judge, tol=REPEAT_TOL):
    """The plan's repeat check (it replaces arm A's "first evaluation is S" check): per item (key,
    ctx, stored judge) a discarded priming render (a new DI or amp) and S through the measure DI,
    judged; every |log| within `tol` of the stored judge on both halves. -> the record."""
    n0, devs = rr.count, {}
    for key, ctx, stored in items:
        rr.render(ctx["di32"], ctx["sel"], ctx["S"])                              # priming, discarded
        j = judge(ctx["ref"], rr.render(ctx["di32"], ctx["sel"], ctx["S"]), ctx["di"], ctx["part"]["judge_lag"])
        devs[key] = max(DS.deviation(j[h], stored[h]) for h in ("A", "B"))
    worst = max(devs.values(), default=0.0)
    return {"groups": list(devs), "devs": devs, "worst": worst, "tol": tol, "primes": len(items),
            "renders": rr.count - n0, "status": "done" if worst <= tol else "stopped"}


def render_group(rr, ctx, rb32, m_todo, d_todo, rec, *, run_dir, judge, keep, save):
    """One (part, amp) group. A discarded priming render through the real rebuild at S, then arm
    A's remaining directions (`run_dir(d)`, each saving its own record with its 55 renders); then
    D's answers through the measure DI, each judged on both halves and kept. Arm A's last renders
    were its judges through the measure DI on the same amp, so D needs no new priming; when arm A
    had nothing left (a resume) the measure DI is primed first. rec: the group's record (its own
    renders and primes, the D judges; resumable by render). -> rec, status done."""
    if m_todo:
        rr.render(rb32, ctx["sel"], ctx["S"])                                     # priming, discarded
        rec["primes"] += 1
        rec["renders"] += 1
        save(rec)
        for d in m_todo:
            run_dir(d)
    todo = [(arm, s, x) for arm, s, x in d_todo if f"{arm}|{s}" not in rec["judge"]]
    if todo:
        if not m_todo:
            rr.render(ctx["di32"], ctx["sel"], ctx["S"])                          # priming, discarded
            rec["primes"] += 1
            rec["renders"] += 1
        for arm, search, x in todo:
            y = rr.render(ctx["di32"], ctx["sel"], x)
            rec["renders"] += 1
            rec["judge"][f"{arm}|{search}"] = judge(ctx["ref"], y, ctx["di"], ctx["part"]["judge_lag"])
            keep(arm, search, y)
            save(rec)
    rec["status"] = "done"
    save(rec)
    return rec


def spent(root):
    """Renders recorded under a run's outputs (arm A's directions, the groups, the repeat check, a smoke)."""
    n = 0
    for sub in ("M", "groups"):
        d = root / sub
        if d.exists():
            n += sum(int((_load(p) or {}).get("renders", 0) or 0) for p in d.rglob("*.json"))
    for name in ("repeat.json", "smoke.json"):
        n += int((_load(root / name) or {}).get("renders", 0) or 0)
    return n


def left(root, dirs, reps):
    """(renders, kept FLACs) still to do for the whole run, by the plan's counts."""
    by = {}
    for d in dirs:
        by.setdefault((d[0], d[1]), []).append(d)
    n = kept = 0
    for (slug, amp), ds in by.items():
        g = _load(group_path(root, slug, amp)) or {}
        if g.get("status") == "done":
            continue
        m = sum(1 for d in ds if not A._done(m_path(root, *d[:3])))
        dn = sum(1 for arm in d_arms(slug) for d in ds if f"{arm}|{d[2]}" not in (g.get("judge") or {}))
        n += m * A.PER_DIRECTION + 1 + dn
        kept += m + dn
    if not A._done(root / "repeat.json"):
        n += 2 * len(reps)
    return n, kept


def primes_check(root, dirs, reps):
    """Recorded priming renders against the plan's (one per group, one per repeat group)."""
    groups = A.groups(dirs)
    per = {f"{s}|{a}": (_load(group_path(root, s, a)) or {}).get("primes") for s, a in groups}
    rep = (_load(root / "repeat.json") or {}).get("primes")
    return {"expected": len(groups) + len(reps), "recorded": sum(v or 0 for v in per.values()) + (rep or 0),
            "repeat": rep, "groups_not_one": {k: v for k, v in per.items() if v != 1}}


# --- "as mixed" (pure) ------------------------------------------------------------------------------

def third_octave_centres(lo=EQ_RANGE[0], hi=EQ_RANGE[1]):
    k0, k1 = math.ceil(3 * math.log2(lo / 1000) - 1e-9), math.floor(3 * math.log2(hi / 1000) + 1e-9)
    return [1000 * 2 ** (k / 3) for k in range(k0, k1 + 1)]


def fit_mix(ref, mix, a, b, sr=SR, max_lag=MAX_LAG, nperseg=EQ_NPERSEG):
    """`reference.wav` carried into a mix, fitted on samples [a, b): the lag at the largest |cross-
    correlation| (the cross-spectrum's inverse, sign free, `mix_previews.best_lag`) within ±max_lag
    (mix[t] ~ ref[t − lag]), then per 1/3 octave |Σ S_xy| / Σ S_xx of the lag-aligned reference
    against the mix (dB, relative to the median band), and the mean magnitude-squared coherence over
    0.2-5 kHz. Not GCC-PHAT: measured on these parts (2026-10-22, zero renders), its whitening locks
    onto the amp track's bleed at lag 0 (wickerman 1-3 read 0 instead of the stems' 398); the plain
    correlation finds the stems' lag on 14 of 17. -> {lag, r, centres_hz, gains_db, coherence}."""
    import numpy as np
    from scipy import signal

    ref, mix = np.asarray(ref, np.float64), np.asarray(mix, np.float64)
    lag, r = MP.best_lag(ref[a:b], mix[a:b], max_lag)
    x, y = MP.shift(ref, lag)[a:b], mix[a:b]
    f, sxy = signal.csd(x, y, fs=sr, nperseg=nperseg)
    _, sxx = signal.welch(x, fs=sr, nperseg=nperseg)
    _, coh = signal.coherence(x, y, fs=sr, nperseg=nperseg)
    cen = third_octave_centres()
    g = []
    for c in cen:
        m = (f >= c * 2 ** (-1 / 6)) & (f < c * 2 ** (1 / 6))
        den = float(sxx[m].sum()) if m.any() else 0.0
        g.append(20 * math.log10(abs(complex(sxy[m].sum())) / den + 1e-20) if den > 0 else math.nan)
    g = np.asarray(g)
    ok = np.isfinite(g)
    if ok.any():
        g = g - float(np.median(g[ok]))
    band = (f >= COH_BAND[0]) & (f <= COH_BAND[1])
    return {"lag": int(lag), "r": float(r), "centres_hz": cen,
            "gains_db": [float(v) if math.isfinite(v) else None for v in g], "coherence": float(np.mean(coh[band]))}


def apply_eq(x, centres, gains_db, sr=SR):
    """A zero-phase EQ: per-bin gain interpolated in log frequency between the band centres (dB),
    constant beyond the ends; bands without a gain are skipped."""
    import numpy as np

    x = np.asarray(x, np.float64)
    pts = [(math.log2(c), g) for c, g in zip(centres, gains_db) if g is not None and math.isfinite(g)]
    if not pts:
        return x.copy()
    lc, gd = (np.asarray(v) for v in zip(*pts))
    f = np.fft.rfftfreq(len(x), 1 / sr)
    gi = np.interp(np.log2(np.maximum(f, 1e-3)), lc, gd)
    return np.fft.irfft(np.fft.rfft(x) * 10 ** (gi / 20), len(x))


def as_mixed_target(ref, fit, sr=SR):
    """The target for one direction: the reference EQ'd by the fit and delayed by its lag."""
    return MP.shift(apply_eq(ref, fit["centres_hz"], fit["gains_db"], sr), fit["lag"])


def flatness_db(fit, band=COH_BAND):
    """The unity control: the SD of the fitted band gains over 0.2-5 kHz (0 when flat)."""
    v = [g for c, g in zip(fit["centres_hz"], fit["gains_db"]) if g is not None and band[0] <= c <= band[1]]
    return statistics.pstdev(v) if len(v) > 1 else None


def as_mixed_parts(run):
    """(parts in the "as mixed" row, parts left out because only one held half is trusted: a direction's
    fit reads its search half of reference.wav, the half that is not trusted)."""
    both = sorted(s for s, h in run.items() if set(h) == {"A", "B"})
    return both, sorted(set(run) - set(both))


def excluded_parts(fits, cmin=COH_MIN):
    """A part is left out of "as mixed" when any of its fits' coherence is below the declared 0.1."""
    return sorted({k.split("|")[0] for k, f in fits.items() if not f["coherence"] >= cmin})


# --- the report (pure) ------------------------------------------------------------------------------

def make_units(dirs, part_of, value_of, arms):
    """Units per direction: {slug, band, cls, amp, search, held, d: {arm: held-half distance}};
    value_of(arm, unit) -> the distance, or None (not there)."""
    units = []
    for slug, amp, search, held in dirs:
        p = part_of(slug)
        u = {"slug": slug, "band": p["band"], "cls": p["gain_class"], "amp": amp, "search": search, "held": held, "d": {}}
        for arm in arms:
            v = value_of(arm, u)
            if v is not None:
                u["d"][arm] = v
        units.append(u)
    return units


def row_filters():
    return {"all": lambda u: True, "lagged": lambda u: u["slug"] in LAGGED,
            "flipped": lambda u: u["slug"] in FLIPPED, "xlance_failures": lambda u: u["slug"] in XLANCE_FAILURES}


def missing(units, arms):
    return sum(1 for u in units for a in arms if a not in u["d"])


def contrast(units, a, b, fixed=FIXED, filters=None):
    """a − b (log of the held distances), per part over amps and halves, band-weighted with the 90%
    band-clustered t interval (`arm_a_levers.effects`), on the directions where every fixed arm and
    a, b score (finite)."""
    filters = filters or row_filters()
    arms = tuple(dict.fromkeys((*fixed, a, b)))
    kept, dropped = R.drop_refused(units, methods=arms)
    kept = [u for u in kept if all(x in u["d"] for x in arms)]
    out = {"directions": len(kept), "dropped": [list(d) for d in dropped], "missing": missing(units, arms), "rows": {}}
    for row, f in filters.items():
        sel = [u for u in kept if f(u)]
        out["rows"][row] = L.effects(sel, a, b) if sel else None
    return out


def penalty_reading(st):
    """The plan's outcome for a real-mix penalty (no pass/fail bar: what the interval says)."""
    if not st or st.get("lo90") is None or st.get("hi90") is None:
        return "incomplete"
    if st["lo90"] > 0:
        return "real mixes hurt (interval above 0)"
    if st["hi90"] < 0:
        return "real mixes help (interval below 0)"
    return "no penalty shown at this power (interval contains 0: undecided, not absent)"


def _all(c):
    return ((c.get("rows") or {}).get("all") or {}).get("all") or {}


def pearson(pairs):
    xs, ys = zip(*pairs) if pairs else ((), ())
    if len(xs) < 3 or statistics.pstdev(xs) == 0 or statistics.pstdev(ys) == 0:
        return None
    return statistics.correlation(xs, ys)


def per_part(units, snr_change, level_shift, lags):
    """Per part: each route's penalty and its gain on S (means over amps and halves), beside the
    stem SNR change (mix-previews' c − b), D's input level shift and the logged mix lag."""
    by = {}
    for u in units:
        by.setdefault(u["slug"], []).append(u)

    def mean_log(us, a, b):
        v = [math.log(u["d"][a] / u["d"][b]) for u in us if _pos(u["d"].get(a)) and _pos(u["d"].get(b))]
        return statistics.fmean(v) if v else None

    out = {}
    for slug, us in sorted(by.items()):
        out[slug] = {"band": us[0]["band"], "directions": len(us),
                     **{n: mean_log(us, a, b) for n, (a, b) in CONTRASTS.items()},
                     "stem_snr_change_db": snr_change.get(slug), "d_input_level_shift_lu": level_shift.get(slug),
                     "mix_lag": lags.get(slug), "lagged": slug in LAGGED, "flipped": slug in FLIPPED}
    corr = {}
    for pen in ("M_penalty", "D_penalty"):
        for x in ("stem_snr_change_db", "d_input_level_shift_lu"):
            pairs = [(r[x], r[pen]) for r in out.values() if r[x] is not None and r[pen] is not None]
            corr[f"{pen}~{x}"] = {"pearson_r": pearson(pairs), "parts": len(pairs)}
    return out, corr


def bw_rows(values, band_of):
    """{slug: [values]} -> the band-weighted mean with the 90% band-clustered t interval (`song_readout.bw_stats`)."""
    rows = [(band_of(s), statistics.fmean(v)) for s, v in sorted(values.items()) if v]
    return R.bw_stats(rows)


def knob_movement(dims, x, y):
    """Mean |Δ| in unit knob space over the continuous dims of two settings ({(module, key): stored})."""
    cs = [d for d in dims if d.kind in ("cont", "log")]
    return statistics.fmean(abs(L.unit(d, x) - L.unit(d, y)) for d in cs) if cs else None


# --- inputs ---------------------------------------------------------------------------------------------

def flat(d, pre=""):
    """A nested dict flattened to {"a/b/c": leaf}."""
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            out.update(flat(v, f"{pre}{k}/"))
        else:
            out[f"{pre}{k}"] = v
    return out


def hash_changes(old, new):
    """The recorded input hashes that a rerun of `inputs` would change (or drop, or add). -> sorted keys."""
    a, b = flat(old), flat(new)
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def alignment_entry(al, slug, kind):
    """(song, crop entry) of the part's crop in `kind`, or (None, None)."""
    for song, e in al.items():
        if song.startswith("_") or kind not in e:
            continue
        c = e[kind].get("crops", {}).get(slug)
        if c is not None:
            return song, c
    return None, None


def cmd_inputs(args):
    """Zero renders: the run set from the trusted list, the inputs' hashes, and the checks (see the
    module docstring); writes inputs.json, ok only if every check passed."""
    import numpy as np
    import soundfile as sf

    from learn import confirm_run as CR

    root = out_root(args)
    tp, entries, sha = read_trusted(args.trusted)
    run, outside = run_set(entries)
    if args.limit:
        if root == OUT:
            raise SystemExit("--limit is for a scratch --out only")
        run = dict(list(run.items())[:args.limit])
    if not run:
        raise SystemExit(f"no trusted part among the plan's {len(PARTS)}: nothing to run")
    old = _load(root / "inputs.json")
    if old and old["trusted"]["sha256"] != sha:
        raise SystemExit("inputs.json was made from another trusted list: start a new --out for a new list")
    slugs = sorted(run)
    dirs = run_dirs(run)
    probs = {}
    held = A.heldout_check(slugs)
    if held:
        probs["heldout"] = held
    al = _load(ALIGNMENT) or {}
    hashes = {"alignment": LO.file_sha256(ALIGNMENT), "real_crop": {}, "mega_real": {}, "parts": {}}
    crops, lags, sflac, bad = {}, {}, {}, {}
    for slug in slugs:
        part = A.f_part(slug)
        ref = CR.mono(part["crop"] / "reference.wav")
        hashes["parts"][slug] = {n: LO.file_sha256(part["crop"] / n) for n in ("reference.wav", "di.wav", "mix.wav")}
        unity = np.load(A.sep_crop("mega53", slug)).astype(np.float64)
        lags[slug] = {"unity": logged_lag(unity, ref)}
        for kind in kinds(slug):
            key = f"{slug}--{kind}"
            song, c = alignment_entry(al, slug, kind)
            if not c or not c.get("covered") or not c.get("stage_f"):
                bad[key] = f"not covered in alignment.json ({kind})"
                continue
            cp, mp = real_crop_path(slug, kind), mega_real_path(slug, kind)
            if not (cp.exists() and mp.exists()):
                bad[key] = "stored real-mix crop or Mega-53 stem missing"
                continue
            hashes["real_crop"][key], hashes["mega_real"][key] = LO.file_sha256(cp), LO.file_sha256(mp)
            x, s = np.load(cp).astype(np.float64), np.load(mp).astype(np.float64)
            if len(x) != CROP or len(s) != CROP or not (np.isfinite(x).all() and np.isfinite(s).all()):
                bad[key] = f"crop {len(x)} / stem {len(s)} samples, or not finite"
                continue
            ctx, o, _ = MP.preview_context(song, kind, slug, c["crop_offset_samples"])
            crops[key] = float(np.max(np.abs(ctx[o:o + CROP].astype(np.float64) - x)))
            if not crops[key] <= CROP_TOL:
                bad[key] = f"the crop re-derived from the preview differs by {crops[key]} (limit {CROP_TOL})"
            lags[slug][kind] = logged_lag(s, ref)
        mk = mastered_kind(slug)
        if mk in lags[slug]:
            d, flip = mix_shift(lags[slug][mk], lags[slug]["unity"])
            lags[slug]["mix_delay"], lags[slug]["mix_flipped"] = d, flip
        di = K.measure_di(part)
        for amp in K.AMPS:                                      # the stored unity side against today's files
            r = _load(A.s_path(slug, amp))
            fp = A.s_path(slug, amp).with_suffix(".flac")
            if not (r and r.get("status") == "done" and fp.exists()):
                continue                                         # reported by stored_problems
            y, _ = sf.read(str(fp), dtype="float64")
            y = np.concatenate([np.zeros(int(A.TRIM_S * SR)), y * r["kept_flac_scale"]])
            j = K.judge(ref, y, di, part["judge_lag"])
            sflac[f"{slug}|{amp}"] = max(DS.deviation(j[h], r["judge"][h]) for h in ("A", "B"))
        print("inputs", slug, {k: v for k, v in lags[slug].items()}, flush=True)
    if bad:
        probs["real_mix_inputs"] = bad
    s_bad = {k: v for k, v in sflac.items() if not v <= S_FLAC_TOL}
    if s_bad:
        probs["stored_S_rejudged"] = s_bad
    pp = provenance_problems(_load(MEGA_REAL / "run.json"), _load(A.fdir("sep", "mega53", "run.json")))
    if pp:
        probs["mega53_provenance"] = pp
    od, ulog = step4_dir(), unity_rebuild_log()
    st = stored_problems(dirs, lambda s, a: A._done(A.s_path(s, a)),
                         lambda s, a, sh: A._done(A.result_path("F", "M", s, a, sh)),
                         lambda s, a: (_load(od / "groups" / f"{s}|{a}.json") or {}).get("status") == "done",
                         lambda s: s in ulog)
    if st:
        probs["stored_unity_side"] = st
    if old and old.get("ok"):
        ch = hash_changes(old.get("hashes"), hashes)
        if ch:
            raise SystemExit(f"inputs changed since `inputs` recorded them ({len(ch)}: {ch[:5]}): the recorded "
                             "hashes stay; investigate, and start a new --out if the change is meant")
    rec = {"plan": PLAN, "ok": not probs, "problems": probs, "smoke": bool(args.limit), "limit": args.limit,
           "trusted": {"path": str(tp), "sha256": sha, "entries": [s if h is None else f"{s}:{h}" for s, h in entries],
                       "outside_this_test": outside},
           "run": run, "parts": len(run), "directions": len(dirs), "groups": len(A.groups(dirs)),
           "expected_renders": expected_renders(dirs), "cap": CAP, "hashes": hashes, "logged_lags": lags,
           "crop_rederived_max_abs": crops, "stored_S_rejudged_dev": sflac,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(root / "inputs.json", rec)
    print(f"inputs: {len(run)} trusted parts of {len(PARTS)}, {len(dirs)} directions, {rec['groups']} groups; "
          f"expected renders {rec['expected_renders']['total']} (cap {CAP}); outside this test {len(outside)}")
    print("ok" if rec["ok"] else json.dumps(probs, indent=1, ensure_ascii=False)[:4000])
    if probs:
        raise SystemExit(1)


# --- separation (D's crop-only stems) ----------------------------------------------------------------

def step4_predictions():
    p = _load(step4_dir() / "predictions.json")
    if not p or p.get("smoke") or p.get("readout_rule") != DS.READOUT_RULE:
        raise SystemExit("step 4's predictions.json (a real one, read by amendment 5) is needed")
    return p


def make_separator(sep_name, device):
    return DS.mega53_separator("fast", device) if sep_name == "mega53" else DS.stem_separator(sep_name, device)


def wait_sep_gate(device):
    while True:
        b = sep_blockers(A._ps(), _own(), A._avail_gb(), device)
        if not b:
            return
        if any("MPS" in x for x in b):
            raise SystemExit(f"{b}: no MPS work while another job may use it (use --device cpu, or wait)")
        print(time.strftime("%H:%M:%S"), "separation gate:", b, flush=True)
        time.sleep(POLL_S)


def cmd_separate(args):
    """D's crop-only stems of the run parts' real-mix crops (mastered, and unmastered where there is
    one) with step 4's separator, as step 4's `stems` made them: the 10-s crop alone. One stored
    unity crop is re-separated first against step 4's stored stem (≥ 40 dB, or stop). Hash-recorded."""
    import numpy as np

    from learn import confirm_run as CR
    from learn import direct_existing as DE

    root, rec = state(args)
    pred4 = step4_predictions()
    sep_name = pred4["stem_sep"]
    d = sep_dir(root, sep_name)
    d.mkdir(parents=True, exist_ok=True)
    man = _load(d / "stems.json") or {"separator": sep_name, "stems": {}}
    for k, v in man["stems"].items():
        if LO.file_sha256(v["path"]) != v["sha256"]:
            raise SystemExit(f"{k}: the stored stem changed since it was recorded")
    slugs = sorted(rec["run"])
    jobs = [(s, k) for s in slugs for k in kinds(s) if f"{s}--{k}" not in man["stems"]]
    if jobs or "repro" not in man:
        wait_sep_gate(args.device)
        sep = make_separator(sep_name, args.device)
        man.update(device=args.device, weights_sha256=getattr(sep, "sha256", None), setting=getattr(sep, "setting", None))
        if "repro" not in man:
            s0 = slugs[0]
            mix_u, _, h = DE.f_inputs(s0, "mega53")
            if h["context"] != pred4["inputs"][s0]["context"]:
                raise SystemExit(f"{s0}: step 4's stored crop changed since its predict")
            stored = DS.stored_stem(_load(DS.stems_manifest_path(DS.ROOT, sep_name)), f"stagef/{s0}")
            db = DS.snr_db(np.asarray(sep(mix_u), np.float64), stored)
            man["repro"] = {"slug": s0, "snr_db": db, "limit_db": SEP_REPRO_DB, "ok": db >= SEP_REPRO_DB}
            _save(d / "stems.json", man)
            print("separator reproduction:", man["repro"], flush=True)
        if not man["repro"]["ok"]:
            raise SystemExit(f"the separator does not reproduce step 4's stored stem: {man['repro']}")
        for slug, kind in jobs:
            key = f"{slug}--{kind}"
            x = load_checked(real_crop_path(slug, kind), rec["hashes"]["real_crop"][key]).astype(np.float64)
            t = time.time()
            s = np.asarray(sep(x), np.float32)
            if len(s) != len(x) or not np.isfinite(s).all():
                raise SystemExit(f"{key}: bad stem")
            p = xl_path(root, sep_name, slug, kind)
            np.save(p.with_suffix(".tmp.npy"), s)
            p.with_suffix(".tmp.npy").replace(p)
            ref = CR.mono(A.f_part(slug)["crop"] / "reference.wav")
            man["stems"][key] = {"path": str(p), "sha256": LO.file_sha256(p), "device": args.device,
                                 "wall_s": round(time.time() - t, 1), "logged_lag": logged_lag(s.astype(np.float64), ref)}
            _save(d / "stems.json", man)
            print("stem", sep_name, key, man["stems"][key]["logged_lag"], flush=True)
    miss = [f"{s}--{k}" for s in slugs for k in kinds(s) if f"{s}--{k}" not in man["stems"]]
    _save(d / "check.json", {"ok": not miss and man["repro"]["ok"], "missing": miss, "separator": sep_name})
    print(f"SEPARATE DONE {sep_name}: {len(man['stems'])} stems; missing {miss}")


# --- rebuild (M_real's search DI) ----------------------------------------------------------------------

def cmd_rebuild(args):
    """C′'s networks hash-checked against stage F's rebuild-log.json, one stored unity M rebuild
    reproduced within 1e-6, then each run part's real-mix Mega-53 stem rebuilt (stage F's recipe)
    and the rebuild-lag check. Writes rebuilt/check.json; any failure stops."""
    import numpy as np

    from learn import song_settings as SS

    root, rec = state(args)
    slugs = sorted(rec["run"])
    A.wait_separation_gate(A.REBUILD_MIN_GB)
    ulog = unity_rebuild_log()
    fo = SS.folds()
    path_of = lambda s: SS.cprime(fo[A.f_part(s)["band"]])  # noqa: E731
    probs = {}
    net = network_problems(slugs, ulog, path_of, LO.file_sha256)
    if net:
        probs["networks"] = net
    ident = None
    if not net:
        s0 = slugs[0]
        tmp = root / "identity"
        A.rebuild_parts([s0], A.f_part, lambda s: np.load(A.sep_crop("mega53", s)), tmp)
        diff = A.identity_diffs(lambda s: np.load(tmp / f"{s}.npy"), lambda s: np.load(A.rebuilt_path("F", "M", s)), [s0])
        ident = {"slug": s0, "max_abs_diff": diff[s0], "tol": IDENTITY_TOL}
        if A.identity_problems(diff, 1):
            probs["identity"] = ident
    log, stop, logged = {}, {}, {}
    if not probs:
        log = A.rebuild_parts(slugs, A.f_part,
                              lambda s: load_checked(mega_real_path(s, mastered_kind(s)),
                                                     rec["hashes"]["mega_real"][f"{s}--{mastered_kind(s)}"]),
                              root / "rebuilt")
        stop, logged = rebuild_lag_problems(log, ulog, slugs)
        if stop:
            probs["rebuild_lag"] = stop
        post = used_network_problems(log, ulog, slugs)
        if post:
            probs["networks_used"] = post
    out = {"ok": not probs, "problems": probs, "identity": ident, "lag_logged_not_stopped": logged,
           "gcc": {s: {"real": (log.get(s) or {}).get("gcc_vs_source"), "unity": (ulog.get(s) or {}).get("gcc_vs_source")}
                   for s in slugs},
           "lufs": {s: (log.get(s) or {}).get("lufs") for s in slugs},
           "sha256": {s: LO.file_sha256(rebuilt_path(root, s)) for s in slugs if rebuilt_path(root, s).exists()},
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(root / "rebuilt" / "check.json", out)
    print("rebuild:", "ok" if out["ok"] else probs, "| logged:", logged, flush=True)
    if probs:
        raise SystemExit(1)


# --- predict (D's answers, zero renders) -----------------------------------------------------------------

def cmd_predict(args):
    """D's answers on the real-mix stems (and the unmastered), step 4's models and pull, after step
    4's unity answers are reproduced; the damping row and the lag/polarity control. Zero renders."""
    import numpy as np

    from learn import direct_existing as DE

    root, rec = state(args)
    pred4 = step4_predictions()
    sep_name = pred4["stem_sep"]
    if not (_load(sep_dir(root, sep_name) / "check.json") or {}).get("ok"):
        raise SystemExit(f"run `separate` first ({sep_name} stems)")
    man = _load(sep_dir(root, sep_name) / "stems.json")
    man4 = _load(DS.stems_manifest_path(DS.ROOT, sep_name))
    gate = DS.step3_gate_record(DS.ROOT)
    label = DS.step4_label(gate, pred4.get("step3_gate"))
    if label:
        print(f"*** D_real {label} ({DS.STEP4_OVERRIDE}; real-mix plan amendment 1) ***", flush=True)
    models, D, _, _ = DS.full_models(DS.ROOT, sep=sep_name)
    if {str(r["seed"]): r["model_sha256"] for r in models["D"][2]} != {str(k): v for k, v in pred4["models"]["D"].items()}:
        raise SystemExit("D's models are not step 4's")
    pulls, cmed = DS.step4_pulls(_load(DS.ROOT / "full" / "readout.json"), models)
    target = pred4["target_mix_lufs"]
    nets = models["D"][0]
    ms = L.menu_S()
    out = {"D_real": {}, "D_unm": {}}
    unity_chk, damping, control, inputs = {}, {}, {}, {}
    for slug in sorted(rec["run"]):
        part = A.f_part(slug)
        cls = part["gain_class"]
        mix_u, _, h = DE.f_inputs(slug, "mega53")
        if h["context"] != pred4["inputs"][slug]["context"]:
            raise SystemExit(f"{slug}: step 4's stored crop changed since its predict")
        stem_u = DS.stored_stem(man4, f"stagef/{slug}")
        if man4["stems"][f"stagef/{slug}"]["sha256"] != pred4["inputs"][slug]["c_f"]:
            raise SystemExit(f"{slug}: step 4's stem changed since its predict")
        side = {"unity": (mix_u, stem_u)}
        for kind in kinds(slug):
            key = f"{slug}--{kind}"
            side["real" if kind != "unmastered" else "unm"] = (
                load_checked(real_crop_path(slug, kind), rec["hashes"]["real_crop"][key]).astype(np.float64),
                load_checked(man["stems"][key]["path"], man["stems"][key]["sha256"]).astype(np.float64))
        gains = {k: DE.inference_gain_db(m, target) for k, (m, _) in side.items()}
        delay, flipped = rec["logged_lags"][slug]["mix_delay"], rec["logged_lags"][slug]["mix_flipped"]
        ctrl_stems = {"lag": MP.shift(stem_u, delay), "sign": -stem_u}
        inputs[slug] = {"gain_db": gains, "mix_delay": delay, "mix_flipped": flipped,
                        "sha256": {k: man["stems"][f"{slug}--{k}"]["sha256"] for k in kinds(slug)}}
        for s_, amp, search, held in run_dirs({slug: rec["run"][slug]}):
            key = f"{slug}|{amp}|{search}"
            _, S = ms[amp][cls]
            cm = DS.masks(amp, cls)[0]
            b, gap = DS.cell_b(pulls["D"], (amp, cls), cm)
            if gap:
                raise SystemExit(f"D {amp} {cls}: {gap} labelled dims have no fitted weight")
            c0 = cmed[(amp, cls)]

            def ans(stem, mix, gain):
                s8, m8, ls, lm = DS.step4_half(stem, mix, search, gain)
                x, c = DS.model_input(s8, m8, ls, lm, search, amp, cls, D)
                cont, sw, mics, diag, _ = DS.answer(nets, x, c, b, c0)
                return {"cont": np.asarray(cont), "a1a2": np.asarray(diag["a1a2"], np.float64),
                        "settings": LO.sdict(DS.settings_from(amp, S, cont, sw, mics)), "diag": diag, "lufs": (ls, lm)}

            res = {k: ans(st, mx, gains[k]) for k, (mx, st) in side.items()}
            stored = pred4["predictions"]["D"][key]
            unity_chk[key] = {"a1a2_max_abs_diff": float(np.max(np.abs(res["unity"]["a1a2"] - np.asarray(
                stored["diag"]["a1a2"], np.float64)))), "settings_equal": res["unity"]["settings"] == stored["settings"]}
            for k, arm in (("real", "D_real"), ("unm", "D_unm")):
                if k in res:
                    out[arm][key] = {"settings": res[k]["settings"], "diag": res[k]["diag"], "cond_lufs": list(res[k]["lufs"]),
                                     "gain_db": gains[k], "held": held,
                                     "level_shift_lu": res[k]["lufs"][0] - res["unity"]["lufs"][0]}
            u, r_ = res["unity"], res["real"]
            damping[key] = {"pre_pull": DS.ensemble_error(r_["a1a2"], u["a1a2"], cm),
                            "post_pull": DS.ensemble_error(r_["cont"], u["cont"], cm),
                            "b_mean": float(np.mean(np.asarray(b, np.float64)[np.asarray(cm, bool)]))}
            control[key] = {n: DS.ensemble_error(ans(st, mix_u, gains["unity"])["cont"], u["cont"], cm)
                            for n, st in ctrl_stems.items()}
        print("predict", slug, {k: round(v, 4) for k, v in gains.items()}, flush=True)
    worst = max((v["a1a2_max_abs_diff"] for v in unity_chk.values()), default=None)
    ok = unity_check_ok(unity_chk)
    res = {"plan": PLAN, "ok": ok, "label": label, "step3_gate": gate, "D": D, "stem_sep": sep_name,
           "readout_rule": DS.READOUT_RULE, "models": {"D": pred4["models"]["D"]}, "target_mix_lufs": target,
           "unity_check": {"worst_a1a2_diff": worst, "tol": A1A2_TOL,
                           "settings_equal": sum(v["settings_equal"] for v in unity_chk.values()),
                           "directions": len(unity_chk), "per_direction": unity_chk},
           "predictions": out, "damping": damping, "control": control, "inputs": inputs, "smoke": rec.get("smoke"),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(root / "predictions.json", res)
    print(f"PREDICT: {len(out['D_real'])} real, {len(out['D_unm'])} unmastered; step 4's unity answers reproduced "
          f"within {worst} (tol {A1A2_TOL}), settings equal {res['unity_check']['settings_equal']}/{len(unity_chk)}"
          + (f" [{label}]" if label else ""))
    if not ok:
        raise SystemExit("step 4's unity answers are not reproduced (A1+A2 within the tolerance and every pulled "
                         "setting equal): D's path or pull differs; stop")


# --- render ---------------------------------------------------------------------------------------------

def _ready(root):
    if (root / "STOP.json").exists():
        raise SystemExit(f"stopped: {root / 'STOP.json'}: {(root / 'STOP.json').read_text()}")
    rb = _load(root / "rebuilt" / "check.json") or {}
    if not rb.get("ok"):
        raise SystemExit("run `rebuild` first (its checks must pass)")
    pred = _load(root / "predictions.json") or {}
    if not pred.get("ok"):
        raise SystemExit("run `predict` first (step 4's unity answers must be reproduced)")
    return rb, pred


def _stop(root, why):
    _save(root / "STOP.json", {"why": why, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    raise SystemExit(f"{why}: every shard stops; investigate, then delete {root / 'STOP.json'}")


def group_inputs(root, rec, rb, slug):
    """The real-mix Mega-53 stem (arm A's reference) and its rebuild (the search DI), hash-checked."""
    import numpy as np

    k = f"{slug}--{mastered_kind(slug)}"
    stem = load_checked(mega_real_path(slug, mastered_kind(slug)), rec["hashes"]["mega_real"][k]).astype(np.float64)
    return stem, load_checked(rebuilt_path(root, slug), rb["sha256"][slug])


def cmd_render(args):
    """The run's renders for one shard of its (part, amp) groups (see the module docstring)."""
    import numpy as np

    root, rec = state(args)
    rb_chk, pred = _ready(root)
    run = rec["run"]
    dirs = run_dirs(run)
    held = A.heldout_check(sorted(run))
    if held:
        raise SystemExit(f"held-out check failed (fail closed): {held}")
    gs = A.groups(dirs)
    reps = repeat_groups(gs)
    n_left, kept = left(root, dirs, reps)
    why = A.cap_problem(spent(root), n_left, CAP)
    if why:
        raise SystemExit(why)
    if not LO.disk_ok(LO.disk_free_gb(), kept):
        raise SystemExit(f"free disk below the {LO.DISK_GUARD_GB:g} GB guard")
    by_group = {}
    for d in dirs:
        by_group.setdefault((d[0], d[1]), []).append(d)
    mine = L._shard(gs, args.shard)
    if pred.get("label"):
        print(f"*** D_real {pred['label']} ***", flush=True)
    wait_render_gate(servers=True)
    guard, ms = L.SwapGuard(), L.menu_S()
    rr = A.renderer()
    try:
        menu = rr.menu()
        if args.shard[0] == 0 and not A._done(root / "repeat.json"):
            items = [(f"{s}|{a}", A.group_ctx(menu, ms, "F", s, a), _load(A.s_path(s, a))["judge"]) for s, a in reps]
            r = repeat_check(rr, items, K.judge)
            _save(root / "repeat.json", r)
            print("repeat check, worst |log|:", r["worst"], flush=True)
            if r["status"] != "done":
                _stop(root, f"repeat check: S moved {r['worst']:.5f} from the stored judge (tolerance {REPEAT_TOL})")
        t0 = time.time()
        while not A._done(root / "repeat.json"):
            if (root / "STOP.json").exists():
                raise SystemExit("stopped by the repeat check")
            if time.time() - t0 > REPEAT_WAIT_S:
                raise SystemExit("shard 0's repeat check has not passed after 30 min: stopping (resumable)")
            print(time.strftime("%H:%M:%S"), "waiting for shard 0's repeat check", flush=True)
            time.sleep(POLL_S)
        for slug, amp in mine:
            gp = group_path(root, slug, amp)
            grec = _load(gp) or {"slug": slug, "amp": amp, "primes": 0, "renders": 0, "judge": {}, "status": "running",
                                 "label_D": pred.get("label")}
            if grec.get("status") == "done":
                continue
            if (root / "STOP.json").exists():
                raise SystemExit("STOP.json present")
            guard.check()
            wait_render_gate(servers=False)
            g_dirs = by_group[(slug, amp)]
            m_todo = [d for d in g_dirs if not A._done(m_path(root, *d[:3]))]
            g_need = len(m_todo) * A.PER_DIRECTION + 1 + len(g_dirs) * len(d_arms(slug))
            why = A.cap_problem(spent(root), g_need, CAP)
            if why:
                _stop(root, why)
            if not LO.disk_ok(LO.disk_free_gb(), len(m_todo) + 2 * len(g_dirs)):
                raise SystemExit(f"free disk below the {LO.DISK_GUARD_GB:g} GB guard (resumable)")
            ctx = A.group_ctx(menu, ms, "F", slug, amp)
            if K.key(dict(ctx["S"])) != K.key(ctx["S_stored"]):
                _stop(root, f"{amp}: the live S differs from the stored copy")
            stem, rb = group_inputs(root, rec, rb_chk, slug)
            d_todo = [(arm, sh, LO.tdict(pred["predictions"][arm][f"{slug}|{amp}|{sh}"]["settings"]))
                      for arm in d_arms(slug) for _, _, sh, _ in g_dirs]

            def run_dir(d, ctx=ctx, stem=stem, rb=rb):
                A.run_direction(rr, ctx, "F", "M", d[0], d[1], d[2], d[3], None, stem=stem, rb=rb,
                                path=m_path(root, *d[:3]))

            def keep(arm, search, y, slug=slug, amp=amp):
                A.save_kept_flac(audio_path(root, slug, amp, arm, search), np.asarray(y))

            render_group(rr, ctx, rb.astype(np.float32), m_todo, d_todo, grec, run_dir=run_dir, judge=K.judge,
                         keep=keep, save=lambda r, gp=gp: _save(gp, r))
            print(slug, amp, {k: round(v[{"A": "B", "B": "A"}[k.split("|")[1]]], 4) for k, v in grec["judge"].items()},
                  "renders", grec["renders"], flush=True)
    finally:
        rr.close()
    print(f"RENDER DONE {args.shard[0]}/{args.shard[1]}; renders this process {rr.count}; spent {spent(root)}", flush=True)


def cmd_smoke(args):
    """Scratch only: one group, 5 renders, one process, only with no other render process running.
    A priming render and S through the real rebuild (arm A's objective on the real stem), a priming
    render and S through the measure DI (judged against the stored S), and D_real once."""
    import numpy as np

    root, rec = state(args)
    if root == OUT:
        raise SystemExit("smoke writes into a scratch --out only")
    rb_chk, pred = _ready(root)
    ps, own = A._ps(), _own()
    busy = A.render_procs(ps, own) + [p for p, c in ps if p not in own and "au_render_server" in c]
    if busy:
        raise SystemExit(f"other render processes are running ({busy}): no smoke now")
    slug, amp, search, held = run_dirs(rec["run"])[0]
    stem, rb = group_inputs(root, rec, rb_chk, slug)
    rr = A.renderer()
    try:
        ctx = A.group_ctx(rr.menu(), L.menu_S(), "F", slug, amp)
        rb32 = rb.astype(np.float32)
        rr.render(rb32, ctx["sel"], ctx["S"])                                     # priming
        y = rr.render(rb32, ctx["sel"], ctx["S"])
        obj, proxy = A.objective(stem, y, rb, search)
        rr.render(ctx["di32"], ctx["sel"], ctx["S"])                              # priming (DI change)
        j_s = K.judge(ctx["ref"], rr.render(ctx["di32"], ctx["sel"], ctx["S"]), ctx["di"], ctx["part"]["judge_lag"])
        x = LO.tdict(pred["predictions"]["D_real"][f"{slug}|{amp}|{search}"]["settings"])
        y_d = rr.render(ctx["di32"], ctx["sel"], x)
        j_d = K.judge(ctx["ref"], y_d, ctx["di"], ctx["part"]["judge_lag"])
        A.save_kept_flac(audio_path(root, slug, amp, "D_real", search), y_d)
        stored = _load(A.s_path(slug, amp))["judge"]
        out = {"slug": slug, "amp": amp, "search": search, "renders": rr.count,
               "objective_S_real": obj, "activity_fallback": proxy, "peak_dbfs_S_real": A.peak_dbfs(y),
               "S_judge": j_s, "S_dev": max(DS.deviation(j_s[h], stored[h]) for h in ("A", "B")),
               "D_real_judge": j_d, "label_D": pred.get("label"), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    finally:
        rr.close()
    _save(root / "smoke.json", out)
    print("SMOKE", json.dumps(out, default=str))


# --- as mixed (zero renders) -------------------------------------------------------------------------------

def flac_restored(path):
    """A kept FLAC with its 0.25-s trim re-padded (every arm alike; the judge is level-matched)."""
    import numpy as np
    import soundfile as sf

    y, _ = sf.read(str(path), dtype="float64")
    y = y.mean(1) if y.ndim == 2 else y
    return np.concatenate([np.zeros(int(A.TRIM_S * SR)), y])


def flac_of(root, arm, slug, amp, search, held):
    """The kept FLAC an arm's held-half score came from (S's own when the arm fell back or was refused),
    or None when it is not there."""
    s = A.s_path(slug, amp).with_suffix(".flac")
    if arm == "S":
        return s
    if arm in ("M_unity", "M_real"):
        p = A.result_path("F", "M", slug, amp, search) if arm == "M_unity" else m_path(root, slug, amp, search)
        r = _load(p)
        if not r or r.get("status") != "done":
            return None
        return s if r.get("fallback") else p.with_name(f"{search}-shrunk.flac")
    g = _load((step4_dir() if arm == "D_unity" else root) / "groups" / f"{slug}|{amp}.json") or {}
    k = f"{'D' if arm == 'D_unity' else arm}|{search}"
    if g.get("status") != "done" or k not in g.get("judge", {}):
        return None
    if not _pos(g["judge"][k][held]):
        return s
    return (step4_dir() / "audio" / slug / amp / f"D-{search}.flac") if arm == "D_unity" else \
        audio_path(root, slug, amp, arm, search)


def cmd_as_mixed(args):
    """The descriptive "as mixed" row (zero renders): per direction, the fit on its search half, the
    unity control, and every arm re-judged against the target from its kept FLAC."""
    import numpy as np

    from learn import confirm_run as CR

    root, rec = state(args)
    fits, control, values = {}, {}, {}
    cache = {}
    parts, half_only = as_mixed_parts(rec["run"])
    for slug in parts:
        part = A.f_part(slug)
        k = f"{slug}--{mastered_kind(slug)}"
        mix = load_checked(real_crop_path(slug, mastered_kind(slug)), rec["hashes"]["real_crop"][k]).astype(np.float64)
        ref = CR.mono(part["crop"] / "reference.wav")
        unity_mix = CR.mono(part["crop"] / "mix.wav")
        di = K.measure_di(part)
        for search in sorted({d[2] for d in run_dirs({slug: rec["run"][slug]})}):
            a, b = (int(t * SR) for t in K.R.HALVES[search])
            fits[f"{slug}|{search}"] = f = fit_mix(ref, mix, a, b)
            cu = fit_mix(ref, unity_mix, a, b)
            control[f"{slug}|{search}"] = {"lag": cu["lag"], "flatness_db": flatness_db(cu), "coherence": cu["coherence"]}
            tgt = as_mixed_target(ref, f)
            for _, amp, sh, held in run_dirs({slug: rec["run"][slug]}):
                if sh != search:
                    continue
                vals = {}
                for arm in FIXED:
                    p = flac_of(root, arm, slug, amp, sh, held)
                    if p is None or not pathlib.Path(p).exists():
                        continue
                    ck = (str(p), sh)
                    if ck not in cache:
                        cache[ck] = K.judge(tgt, flac_restored(p), di, part["judge_lag"] + f["lag"])[held]
                    vals[arm] = cache[ck]
                values[f"{slug}|{amp}|{sh}"] = vals
        print("as mixed", slug, {k: (v["lag"], round(v["coherence"], 3)) for k, v in fits.items() if k.startswith(slug + "|")},
              flush=True)
    out = {"plan": PLAN, "fits": fits, "unity_control": control, "excluded_parts": excluded_parts(fits),
           "half_only_parts_left_out": half_only, "coherence_min": COH_MIN, "values": values,
           "note": NOTES["coherence"], "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(root / "as-mixed.json", out)
    print(f"AS MIXED: {len(values)} directions; parts left out (coherence < {COH_MIN}): {out['excluded_parts']}; "
          f"left out with one trusted half only (the fit would read the untrusted half): {half_only}")


# --- report ---------------------------------------------------------------------------------------------

def unit_values(root, step4_groups):
    """value_of(arm, unit) for the report: S, stage F's M and step 4's D stored; M_real and D_real (and
    D_unm) from this run. A fallback (M) or a refused answer (D) scores as S. -> (value_of, refused: {arm:
    the set of refused (slug, amp, search)}, so a direction read by several unit lists counts once)."""
    refused = {"D_unity": set(), "D_real": set(), "D_unm": set()}

    def s_of(u):
        r = _load(A.s_path(u["slug"], u["amp"]))
        return r["judge"][u["held"]] if r and r.get("status") == "done" else None

    def value_of(arm, u):
        s = s_of(u)
        if arm == "S":
            return s
        if arm in ("M_unity", "M_real"):
            p = A.result_path("F", "M", u["slug"], u["amp"], u["search"]) if arm == "M_unity" else \
                m_path(root, u["slug"], u["amp"], u["search"])
            r = _load(p)
            if not r or r.get("status") != "done":
                return None
            return s if r.get("fallback") else r["judge_shrunk"][u["held"]]
        g = step4_groups(u["slug"], u["amp"]) if arm == "D_unity" else _load(group_path(root, u["slug"], u["amp"])) or {}
        k = f"{'D' if arm == 'D_unity' else arm}|{u['search']}"
        if g.get("status") != "done" or k not in g.get("judge", {}):
            return None
        v = g["judge"][k][u["held"]]
        if not _pos(v):
            refused[arm].add((u["slug"], u["amp"], u["search"]))
            return s
        return v

    return value_of, refused


def report_from_units(units, unm_units, dirs):
    """The contrasts, their readings and the unmastered row (pure)."""
    rep = {"contrasts": {}, "unmastered": {}, "readings": {}, "complete": {}}
    for name, (a, b) in CONTRASTS.items():
        rep["contrasts"][name] = contrast(units, a, b)
    rep["complete"] = {"directions": len(dirs), "missing_arm_results": missing(units, FIXED)}
    for name in PRIMARY:
        rep["readings"][name] = penalty_reading(_all(rep["contrasts"][name]))
    for name, (a, b) in UNM_CONTRASTS.items():
        rep["unmastered"][name] = contrast(unm_units, a, b, fixed=FIXED + ("D_unm",), filters={"all": lambda u: True})
    return rep


def cmd_report(args):
    """The report (see the module docstring); writes report.json."""
    root, rec = state(args)
    run = rec["run"]
    dirs = run_dirs(run)
    reps = repeat_groups(A.groups(dirs))
    pred = _load(root / "predictions.json") or {}
    od = step4_dir()
    s4 = {}

    def step4_groups(slug, amp):
        if (slug, amp) not in s4:
            s4[(slug, amp)] = _load(od / "groups" / f"{slug}|{amp}.json") or {}
        return s4[(slug, amp)]

    value_of, refused = unit_values(root, step4_groups)
    part_of = A.f_part
    units = make_units(dirs, part_of, value_of, FIXED)
    unm = make_units([d for d in dirs if d[0] in UNMASTERED], part_of, value_of, FIXED + ("D_unm",))
    rep = {"plan": PLAN, "label_D": pred.get("label"), "trusted": rec["trusted"], "run": run,
           "directions": len(dirs), **report_from_units(units, unm, dirs),
           "refused_scored_as_S": {a: len(v) for a, v in refused.items()}}
    band_of = lambda s: A.pool_band(s)  # noqa: E731
    mp = (_load(MP_REPORT) or {}).get("parts", {})
    snr = {s: mp[k]["snr_db"]["c_real_stem"] - mp[k]["snr_db"]["b_unity_stem"]
           for s in run for k in (f"{s}|{mastered_kind(s)}",) if k in mp}
    lvl, damp, ctrl = {}, {}, {}
    for key, v in (pred.get("predictions") or {}).get("D_real", {}).items():
        lvl.setdefault(key.split("|")[0], []).append(v["level_shift_lu"])
    lags = {s: {k: rec["logged_lags"][s].get(k) for k in ("mix_delay", "mix_flipped")} for s in run}
    rep["per_part"], rep["per_part_correlations"] = per_part(units, snr, {s: statistics.fmean(v) for s, v in lvl.items()},
                                                             lags)
    for key, v in (pred.get("damping") or {}).items():
        for n, x in v.items():
            damp.setdefault(n, {}).setdefault(key.split("|")[0], []).append(x)
    for key, v in (pred.get("control") or {}).items():
        for n, x in v.items():
            ctrl.setdefault(n, {}).setdefault(key.split("|")[0], []).append(x)
    m_move = {"best": {}, "shrunk": {}}
    ms = L.menu_S()
    for slug, amp, search, held in dirs:
        ru, rr_ = _load(A.result_path("F", "M", slug, amp, search)), _load(m_path(root, slug, amp, search))
        if not (ru and rr_ and ru.get("status") == rr_.get("status") == "done"):
            continue
        dims = K.space(amp, ms[amp][A.f_part(slug)["gain_class"]][1])
        for n in ("best", "shrunk"):
            m_move[n].setdefault(slug, []).append(knob_movement(dims, LO.tdict(rr_["settings"][n]), LO.tdict(ru["settings"][n])))
    rep["damping"] = {"D": {n: bw_rows(v, band_of) for n, v in damp.items()},
                      "M_knob_movement": {n: bw_rows(v, band_of) for n, v in m_move.items()},
                      "note": "D: mean |Δ| real against unity over the labelled continuous dims, before (A1+A2) and after "
                              "amendment 5's pull, with the mean pull weight b; M: the same in unit knob space for arm "
                              "A's unshrunk best and its shrink-0.5 output"}
    rep["control"] = {"D_movement": {n: bw_rows(v, band_of) for n, v in ctrl.items()},
                      "D_real_movement": bw_rows(damp.get("post_pull", {}), band_of),
                      "note": "zero renders: D's answer with the unity stem shifted by the part's mix lag ('lag') or "
                              "sign-flipped ('sign'), against its unity answer; beside it the real mix's own movement"}
    am = _load(root / "as-mixed.json")
    if am:
        ex = set(am["excluded_parts"]) | set(am.get("half_only_parts_left_out", [])) | set(as_mixed_parts(run)[1])

        def am_value(arm, u):
            return (am["values"].get(f"{u['slug']}|{u['amp']}|{u['search']}") or {}).get(arm)

        am_units = make_units([d for d in dirs if d[0] not in ex], part_of, am_value, FIXED)
        rep["as_mixed"] = {"note": "descriptive; the EQ'd target changes the judge's bands, so not comparable with the "
                                   "primary; cannot capture compression or reverb tails",
                           "excluded_parts": sorted(ex), "coherence_left_out": am["excluded_parts"],
                           "half_only_left_out": as_mixed_parts(run)[1],
                           "parts_in_row": len(set(run) - ex), "parts": len(run),
                           "contrasts": {n: contrast(am_units, a, b) for n, (a, b) in CONTRASTS.items()},
                           "unity_control": am["unity_control"],
                           "fit_lags": {k: f["lag"] for k, f in am["fits"].items()},
                           "fit_coherence": {k: f["coherence"] for k, f in am["fits"].items()}}
    sep_name = pred.get("stem_sep") or "xlance_g"
    rep["checks"] = {"inputs_logged_lags": rec["logged_lags"],
                     "rebuild": _load(root / "rebuilt" / "check.json"),
                     "separator": {k: v for k, v in (_load(sep_dir(root, sep_name) / "stems.json") or {}).items() if k != "stems"},
                     "d_stem_logged_lags": {k: v.get("logged_lag") for k, v in
                                            ((_load(sep_dir(root, sep_name) / "stems.json") or {}).get("stems") or {}).items()},
                     "unity_answers": {k: v for k, v in (pred.get("unity_check") or {}).items() if k != "per_direction"},
                     "repeat": _load(root / "repeat.json"), "primes": primes_check(root, dirs, reps),
                     "fallbacks": {"M_real": sum(1 for d in dirs if (_load(m_path(root, *d[:3])) or {}).get("fallback")),
                                   "M_unity": sum(1 for d in dirs if (_load(A.result_path("F", "M", *d[:3])) or {}).get("fallback"))}}
    rep["renders"] = {"spent": spent(root), "expected": expected_renders(dirs), "cap": CAP}
    rep["notes"] = NOTES
    rep["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save(root / "report.json", rep)

    def f(s):
        if not s or s.get("band_weighted_mean") is None:
            return "n/a"
        lo, hi = s.get("lo90"), s.get("hi90")
        return (f"{s['band_weighted_mean']:+.3f}" + ("" if lo is None else f" [{lo:+.3f}, {hi:+.3f}]")
                + f" ({s['bands']} bands)")

    if rep["label_D"]:
        print(f"*** D rows: {rep['label_D']} ***")
    print(f"{len(run)} trusted parts, {len(dirs)} directions; missing arm results {rep['complete']['missing_arm_results']}; "
          f"renders {rep['renders']['spent']} (expected {rep['renders']['expected']['total']}, cap {CAP})")
    for name, c in rep["contrasts"].items():
        print(f"{'*' if name in PRIMARY else ' '} {name:18s} " + "  ".join(
            f"{r}: {f((c['rows'].get(r) or {}).get('all'))}" for r in ROWS))
    for name in PRIMARY:
        print(f"  {name}: {rep['readings'][name]}")
    for name, c in rep["unmastered"].items():
        print(f"  unmastered {name}: {f(_all(c))}")
    print("  priming", rep["checks"]["primes"]["recorded"], "of", rep["checks"]["primes"]["expected"],
          "| fallbacks", rep["checks"]["fallbacks"], "| D refused scored as S", rep["refused_scored_as_S"])
    for n in NOTES.values():
        print("  note:", n)


# --- main -----------------------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("inputs", "separate", "rebuild", "predict", "render", "smoke", "as-mixed", "report"))
    ap.add_argument("--trusted", help="the trusted-parts list (required by every command)")
    ap.add_argument("--out", help="a scratch output root instead of ~/ndsp-presets/learn/real-mix-test")
    ap.add_argument("--limit", type=int, help="inputs: keep the first K run parts (scratch --out only)")
    ap.add_argument("--device", choices=("cpu", "mps"), default="cpu",
                    help="separate: CPU (default; 4 threads) or MPS, refused while another job may use the GPU")
    ap.add_argument("--shard", default="0/1")
    a = ap.parse_args(argv)
    if not a.trusted:
        ap.error("--trusted FILE is required: the test runs on trusted parts only")
    a.shard = tuple(int(x) for x in a.shard.split("/"))
    {"inputs": cmd_inputs, "separate": cmd_separate, "rebuild": cmd_rebuild, "predict": cmd_predict,
     "render": cmd_render, "smoke": cmd_smoke, "as-mixed": cmd_as_mixed, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    main()
