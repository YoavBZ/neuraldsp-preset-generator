"""Arm A with Mega-53 (`docs/arm-a-mega53-plan.md`; amendment 1 governs where it differs): does
the better separator land arm A's adopted recipe closer to the record? Development only;
estimates with 90% band-clustered intervals, no pass/fail bars.

    .venv/bin/python -m learn.arm_a_mega53 decide-x                     # once, after report-1d.json; zero renders
    .venv/bin/python -m learn.arm_a_mega53 contexts                     # stage F: 30-s full mixes (CPU, light)
    $TORCH_PY -m learn.arm_a_mega53 separate --sep htdemucs             # CPU, 2 threads, behind the gate
    $MSST_PY  -m learn.arm_a_mega53 separate --sep mega53               # CPU, 4 threads, memory gate
    $TORCH_PY -m learn.arm_a_mega53 rebuild --sep htdemucs              # identity check, then stage F's rebuilds
    $TORCH_PY -m learn.arm_a_mega53 rebuild --sep mega53
    $TORCH_PY -m learn.arm_a_mega53 rebuild --sep x                     # only if decide-x added arm X
    .venv/bin/python -m learn.arm_a_mega53 check-inputs                 # zero renders; gates stage F
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.arm_a_mega53 search --stage D --shard i/3
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.arm_a_mega53 search --stage F --shard i/3
    .venv/bin/python -m learn.arm_a_mega53 report --stage D             # and --stage F

TORCH_PY is ~/ndsp-presets/tools/demucs-venv/bin/python, MSST_PY ~/ndsp-presets/tools/msst-venv/bin/python.
Outputs go to ~/ndsp-presets/learn/arm-a-mega53/. `learn/arm_a_mega53_run.zsh` chains the plan's
launch order unattended.

The recipe (fixed; only the stem and its rebuild change), per direction, part and amp, from the
part's class's S: the rebuilt-DI main stage (`arm_a_levers.main_stage`, 52 renders, seed
20261013, `rebuilt_distance` on the search half at lag −52 with its activity fallback), shrink 0.5
(`arm_a_levers.shrink`), the fallback to S (the shrunk setting rendered once through the arm's own
rebuild: peak after the first 0.25 s below −60 dBFS, or a non-finite search-half objective), and the
judge through the measure DI on both halves (`knob_ceiling.judge`). Every render goes through
`knob_ceiling.Renderer` (isolate=True, process reuse).

The pure parts (the pool, the held-out check, decide-x, the recipe, the fallback rule, the gates,
the sharding, the counts, the rows and the report's contrasts) are unit-tested with fakes; the
commands that render or separate are not, like the other step modules.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import random
import re
import subprocess
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(PLUGIN_ROOT / "research"))

from learn import arm_a_levers as L  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn import local_objective as LO  # noqa: E402
from learn import local_objective_1c as C  # noqa: E402
from learn import song_readout as R  # noqa: E402

OUT = K.HOME / "learn/arm-a-mega53"
SR = 48000
CROP = 480_000
STAGES = ("D", "F")

# --- the recipe (the adopted one: levers 3-C′ with shrink 0.5) -------------------------------------
SEED = L.SEED                                    # 20261013
OBJ_LAG = L.OBJ_LAG                              # −52
SHRINK = 0.5
MAIN_RENDERS = max(1, round(L.BUDGET * K.SHARES["main"]))     # round(150 × 0.35) = 52
PER_DIRECTION = MAIN_RENDERS + 1 + 2             # search, fallback check, two judges = 55
SILENT_DBFS = -60.0
TRIM_S = 0.25                                    # the isolate fade-in: left out of the peak and of kept audio
TOL = K.REPEAT_TOL                               # 0.005, |log|
REPEAT_SEED = 20261034                           # stage D's repeat-check draw
BAND_ORDER_SEED = 20261035                       # amendment 1, item 4: withdrawn (stage F is a fixed set)
REPEAT_N = 6
REPEAT_WAIT_S = 1800                             # shards 1 and 2 wait this long for shard 0's repeat check

# --- checks on the inputs --------------------------------------------------------------------------
IDENTITY_TOL = 1e-6                              # amendment 1, item 7
LAG_TOL = 3                                      # samples
LUFS_TARGET = LO.REBUILD_LUFS                    # −22.9
LUFS_TOL = LO.REBUILD_LUFS_TOL                   # 0.05 LU
LINEUP_TOL = 1e-6

# --- renders: the plan's tables (amendment 1) ------------------------------------------------------
N_DIRS = {"D": 142, "F": 126}
N_GROUPS = {"D": 72, "F": 63}                    # (part, amp)
CAPS = {"D": 16_500, "F": 14_600}
CAPS_X = {"D": 8_200, "F": 7_300}                # +15,500 in all for X (D's +8,200 stated; F the rest)
TABLE = {"D": 15_990, "F": 14_112}
TABLE_X = {"D": 7_882, "F": 6_993}

# --- the machine (amendment 1, item 6) -------------------------------------------------------------
RENDER_CAP = 3                                   # render processes machine-wide
RENDER_CAP_SEPARATING = 2                        # while a separation runs
SEP_MAX_RENDERS = 2                              # a separation starts only with at most this many
POLL_S = 60
RENDERS = (*LO.RENDERS,
           r"-m learn\.arm_a_mega53 search\b",
           r"-m learn\.oracle_di_arm search\b",
           r"-m learn\.perfect_sep_arm search\b",
           r"-m learn\.arm_a_levers (repeat-check|judge-variants|judge-early|screen|local|early-search)\b",
           r"-m learn\.knob_ceiling (run|control|cross)\b",
           r"-m learn\.label_table (render|check)\b",
           r"-m learn\.song_settings (arm-a|menu-pick|control-render|control-search|arm-c)\b")
SEPARATIONS = (*LO.SEPARATIONS, r"-m learn\.arm_a_mega53 (separate|rebuild)\b")
REBUILD_MIN_GB = 2.0                             # a rebuild needs little memory; the render count still gates it

# --- stage F's pool (amendment 1, item 1): S's stored score finite on both halves on all 3 amps ----
F_POOL = {
    "Atlantis Bound": ("cambridge-It_Was_My_Fault_For_Waiting-ElecGtr3",),
    "The Travelling Band": ("cambridge-Passing_Ships-ElecGtr2", "cambridge-Passing_Ships-ElecGtr4",
                            "cambridge-Quicksand-ElecGtr2"),
    "Zeno": ("cambridge-Signs-ElecGtr3",),
    "Eat The Feeder": ("cambridge-Today's_The_Day-ElecGtr07", "cambridge-wickerman-elecgtr1",
                       "cambridge-wickerman-elecgtr2", "cambridge-wickerman-elecgtr3", "cambridge-wickerman-elecgtr7"),
    "Diesel13": ("cambridge-colour-me-red-elecgtr02", "cambridge-colour-me-red-elecgtr03"),
    "Wall Of Death": ("cambridge-femme-elecgtr5",),
    "Magician's Nephew": ("cambridge-get-out-of-bed-elecgtr2",),
    "Szymon Skiba": ("cambridge-let-s-dance-elecgtr3", "cambridge-let-s-dance-elecgtr4"),
    "Turbosauro": ("cambridge-magilla-elecgtr1",),
    "Dom McLennon": ("telefunken-Gym_Hours-GTR_2", "telefunken-Russian_Cream-GTR_1"),
    "Bernard Purdie Tribute All-Stars": ("telefunken-She's_Gone-GTR",),
    "Doom Flamingo": ("telefunken-Strangest_Places-GTR",),
}
F_SONG = ("cambridge-wickerman-elecgtr1", "cambridge-wickerman-elecgtr2", "cambridge-wickerman-elecgtr3",
          "cambridge-wickerman-elecgtr7", "cambridge-let-s-dance-elecgtr3", "cambridge-let-s-dance-elecgtr4",
          "telefunken-Strangest_Places-GTR", "telefunken-She's_Gone-GTR")
F_BAND_PARTS = ("cambridge-let-s-dance-elecgtr3", "cambridge-let-s-dance-elecgtr4", "telefunken-She's_Gone-GTR")
EXCLUDED_D = ("telefunken-Honey-GTR",)
MUSDB_TEST_BANDS = ("Zeno",)                     # Signs is in MUSDB18 test (review suggestion)
SNR_MIN_DB = 1.0

# --- arms and contrasts -------------------------------------------------------------------------------
ARMS = {"D": ("H", "M", "T"), "F": ("H", "M")}   # X is added by decide-x
BASE = ("S", "H", "M")                           # amendment 1, item 3: the primaries' directions
PRIMARY = ("M", "H")
STORED_S = {"M": ("cprime_mega53", "cprime_mega53|mega53|native|own"),
            "T": ("cprime_ref", "cprime_ref|reference|native|own"),
            "X:mega53": ("csep_mega53", "csep_mega53|mega53|native|own"),
            "X:stem": ("csep_stem", "csep_stem|stem|native|own")}
SEP_SOURCE = {"htdemucs": "stem", "mega53": "mega53"}         # stage F's separators -> 1d's source names
X_P1, X_P2 = "P1_sepnet_stem_minus_current", "P2_sepnet_mega53_minus_mega53"


def _save(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    K._atomic(path, obj)


def _load(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.exists() else None


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


# --- the pool and the held-out check (amendment 1, items 1 and 2) -----------------------------------

def pool_slugs():
    return sorted(s for v in F_POOL.values() for s in v)


def pool_band(slug):
    return next(b for b, v in F_POOL.items() if slug in v)


def s_finite_everywhere(menu, start_names):
    """The pool rule: S's stored `flat` score finite (and positive) on both halves for every amp.
    menu: label-table `menu.json`; start_names: {amp: S's menu name}."""
    for amp, name in start_names.items():
        for h in ("A", "B"):
            v = menu.get(amp, {}).get(name, {}).get("flat", {}).get(h)
            if not (_num(v) and v > 0):
                return False
    return True


def pool_by_rule(lt_parts, step3, menu_of):
    """The fresh parts (clean or crunch, outside step 3) passing the S rule. menu_of(slug) -> the
    label table's menu.json (or None: refused)."""
    out = []
    for slug, p in sorted(lt_parts.items()):
        if slug in step3:
            continue
        m = menu_of(slug)
        if m is not None and s_finite_everywhere(m, {a: K.START[p["gain_class"]][a] for a in K.AMPS}):
            out.append(slug)
    return out


def set12_slug(source, song, part):
    """`label_table.build_parts`'s slug for a set 1–2 part."""
    return "-".join(x.replace("/", "_").replace(" ", "_") for x in (source, song, part))


def _mentions(obj, needles):
    s = json.dumps(obj, ensure_ascii=False)
    return [n for n in needles if n and n in s]


def heldout_problems(slugs, lt_parts, cat12, cat3, ledger3, covers=None):
    """Amendment 1, item 2: every stage-F part must be found in its catalogue and be development,
    with no held-out use; it fails closed (a part not found is a problem, never a pass).
    - sets 1–2 (`docs/validation-datasets.json`): the session (matched by slug) has
      split == "development", is in no `held_out_uses` entry, and is not Guitar-TECHS P3;
    - set 3 (`docs/validation-set3.json`): the part (matched by slug) has split == "development",
      its band is not a held-out band, and no `held_out_uses` entry names it. The set-3 ledger
      (`docs/set3-heldout-use-ledger.json`) counts uses, not sessions, so the real check is the
      catalogue's split field and its empty `held_out_uses`; the ledger is only scanned for the
      part's slug or session as an extra, fail-closed check;
    - no part from sets 4, 5 or 6: `covers(x)` (True if any of their catalogues covers x) on the
      slug, band and crop folder.
    -> {slug: [problems]} (empty: every part passes)."""
    out = {}
    by12 = {}
    for s in cat12.get("sessions", []):
        for p in s.get("parts", []):
            by12.setdefault(set12_slug(s["source"], s["song"], p["part"]), []).append(s)
    by3 = {}
    for p in cat3.get("parts", []):
        by3.setdefault(p.get("slug"), []).append(p)
    held3 = set(cat3.get("held_out_bands", []))
    for slug in slugs:
        bad = []
        p = lt_parts.get(slug)
        if p is None:
            out[slug] = ["not in the label table"]
            continue
        st = p.get("set")
        if st == 12:
            ss = by12.get(slug, [])
            if len(ss) != 1:
                bad.append(f"{len(ss)} sessions match in validation-datasets.json (need exactly 1)")
            for s in ss:
                key = f"{s['source']}/{s['song']}"
                if s.get("split") != "development":
                    bad.append(f"session {key} split {s.get('split')!r}")
                if any(key in (u.get("sessions") or []) for u in cat12.get("held_out_uses", [])):
                    bad.append(f"session {key} has a held_out_uses entry")
                if s["source"].lower() == "guitar-techs" and str(s["song"]).startswith("P3"):
                    bad.append("Guitar-TECHS P3")
        elif st == 3:
            ps = by3.get(slug, [])
            if len(ps) != 1:
                bad.append(f"{len(ps)} parts match in validation-set3.json (need exactly 1)")
            for q in ps:
                if q.get("split") != "development":
                    bad.append(f"set-3 split {q.get('split')!r}")
                if q.get("band") in held3 or p.get("band") in held3:
                    bad.append(f"band {q.get('band')!r} is a held-out band")
                needles = (slug, q.get("session_key"))
                if any(_mentions(u, needles) for u in cat3.get("held_out_uses", [])):
                    bad.append("named in validation-set3.json held_out_uses")
                if _mentions(ledger3.get("uses", []), needles):
                    bad.append("named in the set-3 held-out use ledger")
        else:
            bad.append(f"set {st!r} (only sets 1–2 and 3 may be used)")
        if covers is None:
            bad.append("no set 4–6 check supplied")
        else:
            for x in (slug, p.get("band"), p.get("crop")):
                try:
                    if covers(x):
                        bad.append(f"covered by sets 4–6: {x!r}")
                except Exception as e:                                   # fail closed
                    bad.append(f"sets 4–6 check failed on {x!r}: {e!r}")
        if bad:
            out[slug] = bad
    return out


def _covers(x):
    from learn import set4, set5, set6

    return set4.covers(x) or set5.covers(x) or set6.covers(x)


def heldout_check(slugs=None):
    """The real catalogues. -> {slug: [problems]}."""
    lt = json.loads((PLUGIN_ROOT / "docs/label-table-parts.json").read_text())["parts"]
    cat12 = json.loads((PLUGIN_ROOT / "docs/validation-datasets.json").read_text())
    cat3 = json.loads((PLUGIN_ROOT / "docs/validation-set3.json").read_text())
    ledger3 = json.loads((PLUGIN_ROOT / "docs/set3-heldout-use-ledger.json").read_text())
    return heldout_problems(pool_slugs() if slugs is None else slugs, lt, cat12, cat3, ledger3, _covers)


def require_heldout_ok():
    bad = heldout_check()
    if bad:
        raise SystemExit(f"held-out check failed (fail closed): {bad}")


def lt_parts():
    return json.loads((PLUGIN_ROOT / "docs/label-table-parts.json").read_text())["parts"]


def f_part(slug):
    p = dict(lt_parts()[slug])
    p["crop"] = pathlib.Path(p["crop"])
    if p["band"] != pool_band(slug):
        raise SystemExit(f"{slug}: label-table band {p['band']!r} is not the plan's {pool_band(slug)!r}")
    return p


def d_parts():
    return {s: p for s, p in K.parts().items() if s not in EXCLUDED_D}


def part_of(stage, slug):
    return d_parts()[slug] if stage == "D" else f_part(slug)


# --- decide-x (zero renders, once) ------------------------------------------------------------------

def decide_x(rep):
    """The plan's mechanical rule on `report-1d.json["primary"]` (row (a), all of Σ, cross-half),
    read literally:
    1. P2 (sepnet on Mega-53 − Mega-53) complete with lo90 > 0: X rebuilds the Mega-53 stem (X − M);
    2. otherwise, P1 (sepnet on the stem − current) complete with lo90 > 0: X rebuilds the
       htdemucs stem (X − H);
    3. otherwise (both intervals contain 0 or lie below it, or the primaries the rule would use
       are missing, refused or without a finite lo90): no arm X. A rule's own primary must be
       complete; the other's completeness does not enter it."""
    prim = (rep or {}).get("primary") if isinstance(rep, dict) else None
    prim = prim if isinstance(prim, dict) else {}

    def lo(name):
        p = prim.get(name)
        if not isinstance(p, dict) or "refused" in p:
            return None
        v = p.get("lo90")
        return v if _num(v) else None

    l1, l2 = lo(X_P1), lo(X_P2)
    f = lambda v: "incomplete" if v is None else f"{v:+.4f}"  # noqa: E731
    if l2 is not None and l2 > 0:
        return {"arm_x": "csep_mega53", "source": "mega53", "contrast": ["X", "M"], "rule": 1,
                "why": f"{X_P2} lo90 {l2:+.4f} > 0"}
    if l1 is not None and l1 > 0:
        return {"arm_x": "csep_stem", "source": "stem", "contrast": ["X", "H"], "rule": 2,
                "why": f"{X_P1} lo90 {l1:+.4f} > 0 ({X_P2} lo90 {f(l2)})"}
    return {"arm_x": None, "source": None, "contrast": None, "rule": 3,
            "why": f"no lo90 above 0 ({X_P1} {f(l1)}, {X_P2} {f(l2)})"}


def x_path():
    return OUT / "x.json"


def x_decision():
    """The recorded decision; refuses to go on without one (decide-x runs before any render)."""
    d = _load(x_path())
    if d is None:
        raise SystemExit("run `decide-x` first (it runs once, before any render)")
    return d["outcome"]


def arms(stage, xd=None):
    xd = x_decision() if xd is None else xd
    return ARMS[stage] + (("X",) if xd.get("arm_x") else ())


def ledger_with_arm_x(ledger, outcome, when):
    """The dev-test ledger with `arm_x` set on the arm-a-mega53 entry (never overwritten)."""
    for t in ledger["tests"]:
        if t.get("test_id") == "arm-a-mega53":
            if "arm_x" not in t:
                t["arm_x"] = {"outcome": outcome["arm_x"] or "none", "rule": outcome["rule"], "why": outcome["why"],
                              "decided": when, "record": "~/ndsp-presets/learn/arm-a-mega53/x.json"}
            return ledger
    raise SystemExit("no arm-a-mega53 entry in docs/dev-test-ledger.json")


def cmd_decide_x():
    p = x_path()
    lp = PLUGIN_ROOT / "docs/dev-test-ledger.json"
    if p.exists():
        rec = json.loads(p.read_text())
        led = json.loads(lp.read_text())
        if not any(t.get("test_id") == "arm-a-mega53" and "arm_x" in t for t in led["tests"]):
            lp.write_text(json.dumps(ledger_with_arm_x(led, rec["outcome"], rec["decided"]), indent=1,
                                     ensure_ascii=False) + "\n")
            print("ledger: arm_x recorded from x.json")
        print("decided already (never revisited):", rec["outcome"])
        return
    src = LO.OUT / "report-1d.json"
    if not src.exists():
        raise SystemExit(f"{src} does not exist yet: decide-x waits for 1d's report")
    rep = json.loads(src.read_text())
    out = decide_x(rep)
    when = time.strftime("%Y-%m-%d %H:%M:%S")
    _save(p, {"outcome": out, "decided": when, "report": str(src), "report_sha256": LO.file_sha256(src),
              "inputs": {k: (rep.get("primary") or {}).get(k) for k in (X_P1, X_P2)},
              "status_1d": rep.get("status")})
    led = ledger_with_arm_x(json.loads(lp.read_text()), out, when)
    lp.write_text(json.dumps(led, indent=1, ensure_ascii=False) + "\n")
    print("arm X:", out)


# --- the recipe -----------------------------------------------------------------------------------

def peak_dbfs(y, trim_s=TRIM_S, sr=SR):
    """The render's peak after its first `trim_s` seconds, dBFS (−inf when silent)."""
    import numpy as np

    y = np.asarray(y, np.float64)
    y = y.mean(1) if y.ndim == 2 else y
    tail = y[int(trim_s * sr):]
    pk = float(np.max(np.abs(tail))) if len(tail) else 0.0
    return 20 * math.log10(pk) if pk > 0 else -math.inf


def fallback_reason(peak, objective, floor=SILENT_DBFS):
    """The fallback to S (product-side only): None, or why the output is S."""
    if peak is None or not peak >= floor:
        return f"silent: peak {peak} dBFS after {TRIM_S} s (floor {floor})"
    if not _num(objective):
        return f"refused: search-half objective {objective}"
    return None


def recipe(dims, S, f, probe, lam=SHRINK, seed=SEED):
    """The adopted recipe on one direction. f(x) -> search-half objective (renders); probe(x) ->
    (peak dBFS, search-half objective) of x through the arm's own rebuild (one render)."""
    best_x, best_v, n = L.main_stage(dims, S, f, seed=seed)
    shrunk = L.shrink(dims, S, best_x, lam)
    peak, obj = probe(shrunk)
    why = fallback_reason(peak, obj)
    return {"best_x": best_x, "best_value": best_v, "evaluations": n, "shrunk_x": shrunk,
            "probe": {"peak_dbfs": peak, "objective": obj}, "fallback": why, "output_x": dict(S) if why else shrunk}


def objective(ref, y, rb, half, lag=OBJ_LAG):
    """Arm A's objective: `rebuilt_distance` on `half` at lag −52, with its activity fallback
    (the same function arm A searched with). -> (distance or inf, used the fallback)."""
    from learn.rebuilt_judge import rebuilt_distance

    a, b = K.R.HALVES[half]
    d, proxy = rebuilt_distance(ref, y, rb, start_s=a, end_s=b, lag=lag)
    return (math.inf if d.distance is None else d.distance), bool(proxy)


# --- render counts, sharding ------------------------------------------------------------------------

def expected_renders(stage, n_dirs, n_groups, live):
    """The plan's per-stage counts. live: the searched arms (stage D: M, T and X; stage F: H, M
    and X)."""
    out = {a: n_dirs * PER_DIRECTION + n_groups for a in live}
    if stage == "D":
        out["H_fallback_checks"] = n_dirs + n_groups
        out["repeat_check"] = 2 * REPEAT_N
    else:
        out["S_and_measure_warm_up"] = 2 * n_groups
    out["total"] = sum(out.values())
    return out


def groups(dirs):
    """(part, amp) groups, so a group's directions share one process and one warm-up per arm."""
    return sorted({(d[0], d[1]) for d in dirs})


def shard_groups(dirs, shard):
    return L._shard(groups(dirs), shard)


def repeat_draw(dirs, n=REPEAT_N, seed=REPEAT_SEED):
    return random.Random(seed).sample(sorted(dirs), n)


def stage_dirs(stage):
    """Stage D: song-settings' 142 used directions (step 3's units after the readout's drop).
    Stage F: the pool × amps × directions (126)."""
    if stage == "D":
        kept, _ = R.drop_refused(L.gathered_units())
        return sorted((u["slug"], u["amp"], u["search"], u["held"]) for u in kept)
    return [(s, a, sh, h) for s in pool_slugs() for a in K.AMPS for sh, h in K.DIRECTIONS]


# --- the machine: gates, stop file, caps, disk ---------------------------------------------------

def _matches(cmd, pats):
    from learn import ks_extend as X

    return X._is_python(cmd) and any(re.search(p, cmd) for p in pats)


def render_procs(ps, own=()):
    return [p for p, c in ps if p not in own and _matches(c, RENDERS)]


def separation_procs(ps, own=()):
    return [p for p, c in ps if p not in own and _matches(c, SEPARATIONS)]


def render_blocker(ps, own=()):
    """A render shard starts only when fewer than 3 render processes run machine-wide (itself not
    counted), or fewer than 2 while a separation runs. -> None, or why it waits."""
    n, sp = len(render_procs(ps, own)), separation_procs(ps, own)
    cap = RENDER_CAP_SEPARATING if sp else RENDER_CAP
    if n >= cap:
        return f"{n} render processes running{' beside a separation' if sp else ''} (cap {cap})"
    return None


def separation_blockers(ps, own, avail_gb, min_gb):
    """A separation starts only when at most 2 render processes run, with no training job, no
    other separation, and the memory gate (1c's: about 11 GB for Mega-53's pruned head). -> [why]."""
    out = []
    n = len(render_procs(ps, own))
    if n > SEP_MAX_RENDERS:
        out.append(f"{n} render processes running (a separation needs at most {SEP_MAX_RENDERS})")
    rest = [(p, c) for p, c in ps if p not in own]
    tr = [p for p, c in rest if C.is_training(c)]
    if tr:
        out.append(f"training processes {tr}")
    sp = separation_procs(ps, own)
    if sp:
        out.append(f"another separation {sp}")
    if min_gb and (avail_gb is None or avail_gb < min_gb):
        out.append(f"available memory {avail_gb} GB, under the {min_gb} GB gate")
    return out


def _own():
    return {os.getpid(), os.getppid()}


def _ps():
    from learn import ks_extend as X

    return X._ps()


def _avail_gb():
    vm = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
    return C.available_gb(vm) if vm else None


def wait_render_gate():
    while True:
        why = render_blocker(_ps(), _own())
        if why is None:
            return
        print(time.strftime("%H:%M:%S"), "render gate:", why, flush=True)
        time.sleep(POLL_S)


def wait_separation_gate(min_gb, memory=True):
    while True:
        b = separation_blockers(_ps(), _own(), _avail_gb() if memory else None, min_gb if memory else 0.0)
        if not b:
            return
        print(time.strftime("%H:%M:%S"), "separation gate:", b, flush=True)
        time.sleep(POLL_S)


def stop_paths():
    """This plan's stop file, and the local-objective experiments' shared one."""
    return (OUT / "STOP.json", LO.stop_path())


SCOPED_ARMS = ("T", "X")                         # descriptive or conditional: a failure stops that arm only


class ArmStopped(Exception):
    """A T or X plumbing check failed: that arm stops in every shard; H, M and S go on."""


def arm_stop_path(stage, arm):
    return OUT / f"STOP-{stage}-{arm}.json"


def arm_stopped(stage, arm):
    return arm in SCOPED_ARMS and arm_stop_path(stage, arm).exists()


def check_stop():
    """The global stop files (any breakage of H, M, S, the repeat check or the inputs)."""
    for p in stop_paths():
        if p.exists():
            raise SystemExit(f"stopped: {p}: {p.read_text()}")


def breakage(rec_path, rec, why, stage=None, arm=None):
    """Record the direction as check_failed and write a stop file. For T and X (amendment 1, item
    3: they can't change a primary) the stop is scoped to that arm and stage (`STOP-<stage>-<arm>`;
    `ArmStopped`, the shard goes on with the other arms); otherwise every shard stops."""
    _save(rec_path, {**rec, "status": "check_failed", "why": why})
    when = time.strftime("%Y-%m-%d %H:%M:%S")
    if arm in SCOPED_ARMS:
        _save(arm_stop_path(stage, arm), {"why": why, "time": when})
        raise ArmStopped(f"{why}: arm {arm} stops in stage {stage}; investigate, then delete {arm_stop_path(stage, arm)}")
    _save(OUT / "STOP.json", {"why": why, "time": when})
    raise SystemExit(f"{why}: every shard stops; investigate, then delete {OUT / 'STOP.json'}")


def spent(stage):
    """Renders recorded under a stage's outputs."""
    root = OUT / stage
    if not root.exists():
        return 0
    return sum(int((json.loads(p.read_text()) or {}).get("renders", 0) or 0) for p in root.rglob("*.json")
               if not p.name.startswith(("report", "check", "log", "inputs", "identity")))


def cap_of(stage, xd):
    return CAPS[stage] + (CAPS_X[stage] if xd.get("arm_x") else 0)


def cap_problem(spent_, planned, cap):
    return None if spent_ + planned <= cap else f"{spent_} spent + {planned} planned exceeds the hard cap {cap}"


def disk_ok(planned):
    return LO.disk_ok(LO.disk_free_gb(), planned)


# --- audio ------------------------------------------------------------------------------------------

def save_kept_flac(path, y, trim_s=TRIM_S, sr=SR):
    """A render kept as audio: the first 0.25 s trimmed, 16-bit FLAC, peak-normalised to 0.99.
    -> the factor that restores the level."""
    import numpy as np
    import soundfile as sf

    y = np.asarray(y, np.float64)
    y = (y.mean(1) if y.ndim == 2 else y)[int(trim_s * sr):]
    peak = float(np.abs(y).max()) if len(y) else 0.0
    scale = peak / 0.99 if peak > 0 else 1.0
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.flac")
    sf.write(str(tmp), y / scale, sr, subtype="PCM_16")
    tmp.replace(path)
    return scale


# --- stage F's inputs: contexts, separation, rebuilds -----------------------------------------------

def fdir(*p):
    return OUT.joinpath("F", *p)


def sep_crop(sep, slug):
    return fdir("sep", sep, "crop", f"{slug}.npy")


def rebuilt_path(stage, arm_or_sep, slug, xd=None):
    """The rebuild an arm searches through."""
    from learn import song_settings as SS

    if stage == "D":
        if arm_or_sep == "H":
            return SS.OUT / "rebuilt" / f"{slug}.npy"
        if arm_or_sep == "M":
            return LO.OUT / LO.REBUILD_DIR["cprime_mega53"] / f"{slug}.npy"
        if arm_or_sep == "T":
            return LO.OUT / LO.REBUILD_DIR["cprime_ref"] / f"{slug}.npy"
        if arm_or_sep == "X":
            return LO.OUT / LO.REBUILD_DIR[xd["arm_x"]] / f"{slug}.npy"
    else:
        name = {"H": "htdemucs", "M": "mega53", "X": "x"}.get(arm_or_sep, arm_or_sep)
        return fdir("rebuilt", name, f"{slug}.npy")
    raise ValueError(arm_or_sep)


def arm_reference(stage, arm, slug, part, xd=None):
    """The search's reference for an arm: the stem it rebuilds (the amp track for T)."""
    import numpy as np

    from learn import confirm_run as CR
    from learn import song_settings as SS

    if stage == "D":
        if arm == "H" or (arm == "X" and xd["source"] == "stem"):
            return SS.stem(slug)
        if arm == "M" or arm == "X":
            return np.load(LO.sep_crop_path("mega53", slug)).astype(np.float64)
        if arm == "T":
            return CR.mono(part["crop"] / "reference.wav")
    else:
        sep = {"H": "htdemucs", "M": "mega53"}.get(arm) or ("mega53" if xd["source"] == "mega53" else "htdemucs")
        return np.load(sep_crop(sep, slug)).astype(np.float64)
    raise ValueError(arm)


def shim_catalog(rec):
    """A one-session catalogue in `learn.separate.context`'s form for a set-3 crop (its tracks
    live under datasets-set3; an absolute path joins past `separate.DATA`)."""
    from learn import set3

    cat = {s["key"]: s for s in json.loads((set3.SET3_ROOT / "catalog.json").read_text())["sessions"]}
    s = cat[rec["session_key"]]
    return {"sessions": [{"source": rec["source"], "song": rec["song"], "path": str(set3.SET3_ROOT / s["path"])}]}


def cmd_contexts():
    """Stage F's 30-s full-mix contexts (`learn.separate.context`, role mix: every included mix
    track at unity, vocals kept; its own line-up asserts), saved as float32; the crop slice must
    equal the crop folder's mix.wav within 1e-6 and be 480,000 samples. Zero renders."""
    import numpy as np
    import soundfile as sf

    from learn import separate as SEP

    require_heldout_ok()
    cat12 = json.loads((PLUGIN_ROOT / "docs/validation-datasets.json").read_text())
    d = fdir("contexts")
    d.mkdir(parents=True, exist_ok=True)
    log = _load(d / "log.json") or {}
    for slug in pool_slugs():
        if slug in log and not log[slug].get("problems") and (d / f"{slug}.npy").exists():
            continue
        part = f_part(slug)
        rec = json.loads((part["crop"] / "record.json").read_text())
        row = {"set": part["set"], "vocal_tracks": len(rec.get("vocal_tracks", []))}
        try:
            cat = cat12 if part["set"] == 12 else shim_catalog(rec)
            mix, _, off = SEP.context(part["crop"], cat)
            crop_in, sr = sf.read(str(part["crop"] / "mix.wav"), dtype="float32")
            seg = mix[off:off + CROP]
            lineup = float(np.max(np.abs(seg - crop_in))) if len(crop_in) == CROP and len(seg) == CROP else None
            row.update(offset=int(off), input_s=len(mix) / SR, lineup_max_abs=lineup, sr=sr,
                       problems=[] if lineup is not None and lineup < LINEUP_TOL and sr == SR else
                       [f"crop slice against mix.wav: {lineup} (limit {LINEUP_TOL}); crop {len(crop_in)} samples"])
            if not row["problems"]:
                np.save(d / f"{slug}.npy", mix.astype(np.float32))
        except (AssertionError, KeyError) as e:
            row["problems"] = [f"context: {e!r}"]
        log[slug] = row
        _save(d / "log.json", log)
        print(slug, row, flush=True)
    bad, missing = C.write_check(d, log, pool_slugs())
    if bad or missing:
        raise SystemExit(f"contexts fail their checks: {bad or missing}")
    print(f"contexts: {len(log)} parts, crop slices exact")


def sep_problems(n, lag=None, need_lag=False):
    p = []
    if n != CROP:
        p.append(f"crop length {n}, not {CROP}")
    if need_lag and (lag is None or abs(lag) > LAG_TOL):
        p.append(f"GCC against the htdemucs crop is {lag} samples (limit ±{LAG_TOL})")
    return p


def cmd_separate(sep):
    """One separator on every pool part's full-mix context, CPU only, behind the gate.
    htdemucs: `learn.separate.GuitarSeparator` (DEVICE=cpu, its 2 threads). Mega-53:
    `separator_screen.MsstSeparator` exactly as 1c (provenance and commit checked, pruned by the
    screen's identity check, 4 threads, MPS fallback off), memory gate and swap guard. Per part:
    480,000 samples, and for Mega-53 GCC against the htdemucs crop within ±3 samples; logged: SNRs
    against reference.wav, Mega-53's level above 6 kHz relative to htdemucs, and the htdemucs
    full-mix stem's SNR beside the label table's instrumental stem."""
    import numpy as np

    from learn import confirm_run as CR
    from learn import label_table as LT
    from learn import rank_margin as RM
    from learn import separator_screen as SCR

    require_heldout_ok()
    if not (_load(fdir("contexts", "check.json")) or {}).get("ok"):
        raise SystemExit("run `contexts` first (its checks must pass)")
    if sep == "mega53" and not (_load(fdir("sep", "htdemucs", "check.json")) or {}).get("ok"):
        raise SystemExit("separate --sep htdemucs first (Mega-53's timing check reads its crops)")
    d = fdir("sep", sep)
    (d / "full").mkdir(parents=True, exist_ok=True)
    (d / "crop").mkdir(parents=True, exist_ok=True)
    log = _load(d / "log.json") or {}
    clog = _load(fdir("contexts", "log.json"))
    todo = [s for s in pool_slugs() if not (s in log and sep_crop(sep, s).exists())]
    if todo:
        if sep == "mega53":
            ident = SCR.out_dir() / "identity.json"
            prune = C.prune_decision(_load(ident))
            gate = C.mem_gate_gb(prune)
        else:
            os.environ["DEVICE"] = "cpu"
            prune, gate = None, C.MEM_GATE_PRUNED_GB
        print(sep, "memory gate", gate, "GB", flush=True)
        wait_separation_gate(gate)
        if sep == "mega53":
            model = SCR.MsstSeparator(prune=prune)
        else:
            from learn.separate import GuitarSeparator

            model = GuitarSeparator()
            if model.device != "cpu":
                raise SystemExit(f"htdemucs runs on {model.device}, not the CPU")
        guard = L.SwapGuard()
        for slug in todo:
            wait_separation_gate(gate, memory=False)                 # memory is ours now
            guard.check()
            part = f_part(slug)
            x = np.load(fdir("contexts", f"{slug}.npy")).astype(np.float32)
            off = clog[slug]["offset"]
            t = time.time()
            y = np.asarray(model(x), np.float32)
            if len(y) != len(x):
                raise SystemExit(f"{slug}: the separator returned {len(y)} samples for {len(x)}")
            crop = y[off:off + CROP]
            ref = CR.mono(part["crop"] / "reference.wav")
            np.save(d / "full" / f"{slug}.npy", y)
            np.save(sep_crop(sep, slug), crop)
            row = {"offset": off, "input_s": len(x) / SR, "wall_s": round(time.time() - t, 1),
                   "snr_db_vs_reference": C.snr_db(crop, ref)}
            if sep == "mega53":
                hd = np.load(sep_crop("htdemucs", slug)).astype(np.float64)
                lag = int(RM.gcc_lag(crop.astype(np.float64), hd))
                row.update(gcc_vs_htdemucs=lag, snr_db_htdemucs=C.snr_db(hd, ref),
                           level_above_6k_db_vs_htdemucs=SCR._band_db(crop.astype(np.float64), hd, 6000, 20000),
                           peak_rss_mb=round(SCR.peak_rss_mb(), 1), problems=sep_problems(len(crop), lag, True))
            else:
                inst = LT.stem_path(slug)
                row["snr_db_label_table_instrumental"] = C.snr_db(CR.mono(inst), ref) if inst else None
                row["problems"] = sep_problems(len(crop))
            log[slug] = row
            _save(d / "log.json", log)
            print(slug, row, flush=True)
        info = model.info() if hasattr(model, "info") else {}
        _save(d / "run.json", {**info, "pruned_by_identity": prune, "memory_gate_gb": gate})
    bad, missing = C.write_check(d, log, pool_slugs())
    if bad or missing:
        raise SystemExit(f"{sep} stems fail the checks: {bad or missing}")
    print(f"{sep}: {len(log)} crops pass")


def rebuild_parts(slugs, part_of_, source, out_dir, net=None, extra_leak=None):
    """Amendment 1, item 7: `local_objective.rebuild_from`'s recipe generalised to any part list
    and source: the fold's final C′ (DONE marker) or `net(fold)`, experiment 4's leak assertion
    (and `extra_leak(band, path, fold)`), re-EQ'd by fold 2's average − fold f's, −22.9 LUFS. The
    fold comes from `song_settings.folds()`. -> the log {slug: {...}} (also rebuild-log.json)."""
    import numpy as np
    import torch

    from learn import di_fine_structure as DF
    from learn import direc as D
    from learn import song_settings as SS
    from learn.direc_check import eq_to, to_lufs

    fo = SS.folds()
    avg = {f: np.load(SS.MODELS / "cache" / f"average-fold{f}.npy") for f in range(4)}
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log = _load(out_dir / "rebuild-log.json") or {}
    nets = {}
    for slug in slugs:
        band = part_of_(slug)["band"]
        f = fo[band]
        path = pathlib.Path(net(f)) if net else SS.cprime(f)
        if not SS.net_ready(path):
            raise SystemExit(f"{path} is not final (no DONE marker)")
        cfg = _load(path.parent / "config.json") or {}
        caches = [pathlib.Path(c) for c in cfg.get("caches", [DF.MODELS / c for c in DF.CACHES])]
        DF.assert_no_leak(band, cfg.get("fold", f), f, DF.train_pool_bands(f, caches))
        if extra_leak:
            extra_leak(band, path, f)
        out = out_dir / f"{slug}.npy"
        if out.exists() and slug in log:
            continue
        if path not in nets:
            nets[path] = D.load_model(path).eval()
        src = np.asarray(source(slug))
        x = D.rebuild(nets[path], src.astype(np.float32), device=torch.device("cpu")).astype(np.float64)
        y = to_lufs(eq_to(x, avg[2] - avg[f]))
        np.save(out, y)
        log[slug] = {"fold": f, "band": band, "network": str(path), "network_sha256": LO.file_sha256(path),
                     "lufs": LO.lufs(y), "gcc_vs_source": LO.gcc_level(y, src), "samples": int(len(y))}
        _save(out_dir / "rebuild-log.json", log)
        print(out_dir.name, slug, "fold", f, log[slug]["lufs"], flush=True)
    return log


def identity_diffs(a_of, b_of, slugs):
    """{slug: max |Δ| between two rebuilds, or None when one is missing or the shapes differ}."""
    import numpy as np

    out = {}
    for s in slugs:
        try:
            a, b = np.asarray(a_of(s)), np.asarray(b_of(s))
        except FileNotFoundError:
            out[s] = None
            continue
        out[s] = float(np.max(np.abs(a - b))) if a.shape == b.shape else None
    return out


def identity_problems(diffs, n_expected, tol=IDENTITY_TOL):
    bad = {s: d for s, d in diffs.items() if d is None or not d <= tol}
    if len(diffs) != n_expected:
        bad["_count"] = f"{len(diffs)} parts compared, not {n_expected}"
    return bad


def cmd_identity(sep):
    """Zero renders: on step 3's 24 parts the generalised rebuild reproduces the stored rebuild of
    the same source within 1e-6 (`song-settings/rebuilt/` for the htdemucs stem, 1c's
    `rebuilt-mega53/` for Mega-53). -> ok."""
    import numpy as np

    from learn import song_settings as SS

    ps = d_parts()
    slugs = sorted(ps)
    src = {"htdemucs": lambda s: SS.stem(s), "mega53": lambda s: np.load(LO.sep_crop_path("mega53", s))}[sep]
    stored = {"htdemucs": lambda s: np.load(SS.OUT / "rebuilt" / f"{s}.npy"),
              "mega53": lambda s: np.load(LO.OUT / LO.REBUILD_DIR["cprime_mega53"] / f"{s}.npy")}[sep]
    tmp = OUT / "identity" / sep
    rebuild_parts(slugs, lambda s: ps[s], src, tmp)
    diffs = identity_diffs(lambda s: np.load(tmp / f"{s}.npy"), stored, slugs)
    bad = identity_problems(diffs, len(slugs))
    rec = {"ok": not bad, "parts": len(diffs), "tol": IDENTITY_TOL,
           "max_abs_diff": max((d for d in diffs.values() if d is not None), default=None),
           "problems": bad, "per_part": diffs}
    _save(OUT / "identity" / f"identity-{sep}.json", rec)
    print(f"identity {sep}: {len(diffs)} parts, largest |Δ| {rec['max_abs_diff']}, ok {rec['ok']}", flush=True)
    return rec["ok"]


def cmd_identity_only(sep):
    """Lane A's first step: the identity check alone (stored inputs only), so a failure shows in
    minutes rather than after the separations."""
    if sep not in ("htdemucs", "mega53"):
        raise SystemExit("the identity check is for htdemucs or mega53")
    wait_separation_gate(REBUILD_MIN_GB)
    if not cmd_identity(sep):
        raise SystemExit(f"{sep}: the generalised rebuild doesn't reproduce the stored rebuilds")


def pair_problems(gcc, lufs_a, lufs_b, target=LUFS_TARGET, tol=LUFS_TOL, lag_tol=LAG_TOL):
    """Stage F's paired rebuild checks (a part's H and M rebuilds): GCC within ±3 samples; each at
    −22.9 LUFS within 0.05, or, where BS.1770's gate puts it outside (amendment 4b), within 0.05 LU
    of the other separator's rebuild of the same part."""
    p = []
    if gcc is None or abs(gcc) > lag_tol:
        p.append(f"GCC between the two rebuilds is {gcc} samples (limit ±{lag_tol})")
    for name, a, b in (("first", lufs_a, lufs_b), ("second", lufs_b, lufs_a)):
        if not _num(a):
            p.append(f"{name} rebuild's loudness {a}")
        elif abs(a - target) > tol and not (_num(b) and abs(a - b) <= tol):
            p.append(f"{name} rebuild at {a:.3f} LUFS: outside {target} ± {tol} and > {tol} LU from the other's {b}")
    return p


def x_pair_problems(gcc, lufs_x, lufs_c, tol=LUFS_TOL, lag_tol=LAG_TOL):
    """Arm X's rebuild against the paired C′ rebuild of the same source (amendment 4b's level rule)."""
    p = []
    if gcc is None or abs(gcc) > lag_tol:
        p.append(f"GCC against the paired C′ rebuild is {gcc} samples (limit ±{lag_tol})")
    if not (_num(lufs_x) and _num(lufs_c) and abs(lufs_x - lufs_c) <= tol):
        p.append(f"loudness {lufs_x} against the paired C′ rebuild's {lufs_c} (limit {tol} LU)")
    return p


def cmd_rebuild(sep):
    """Stage F's rebuilds. htdemucs and Mega-53: the identity check on step 3's parts first (a
    failure stops), then the pool's crops through each part's fold's C′. x: decide-x's arm, through
    1d's pinned separator-robust networks (`assert_sepnet_ok` per part), its stage-D rebuilds being
    1d's own (their check must have passed)."""
    import numpy as np

    from learn import local_objective_1d as LD

    require_heldout_ok()
    wait_separation_gate(REBUILD_MIN_GB)
    if sep in ("htdemucs", "mega53"):
        if not (_load(fdir("sep", sep, "check.json")) or {}).get("ok"):
            raise SystemExit(f"{sep}: the separation checks have not passed")
        if not cmd_identity(sep):
            raise SystemExit(f"{sep}: the generalised rebuild doesn't reproduce the stored rebuilds")
        log = rebuild_parts(pool_slugs(), f_part, lambda s: np.load(sep_crop(sep, s)), fdir("rebuilt", sep))
        missing = [s for s in pool_slugs() if s not in log]
        _save(fdir("rebuilt", sep, "check.json"), {"ok": not missing, "missing": missing})
        if missing:
            raise SystemExit(f"{sep}: rebuilds missing {missing}")
        print(f"{sep}: {len(log)} rebuilds")
        return
    xd = x_decision()
    if not xd.get("arm_x"):
        print("decide-x added no arm X: nothing to rebuild")
        return
    if not LO.rebuilds_ok(xd["arm_x"]):
        raise SystemExit(f"{xd['arm_x']}: 1d's rebuild checks (stage D's X rebuilds) have not passed")
    src_sep = "mega53" if xd["source"] == "mega53" else "htdemucs"
    if not (_load(fdir("rebuilt", src_sep, "check.json")) or {}).get("ok"):
        raise SystemExit(f"rebuild --sep {src_sep} first (X's level check reads its rebuilds)")
    log = rebuild_parts(pool_slugs(), f_part, lambda s: np.load(sep_crop(src_sep, s)), fdir("rebuilt", "x"),
                        net=LD.net_path, extra_leak=LD.assert_sepnet_ok)
    missing = [s for s in pool_slugs() if s not in log]
    _save(fdir("rebuilt", "x", "check.json"), {"ok": not missing, "missing": missing, "source": src_sep})
    if missing:
        raise SystemExit(f"x: rebuilds missing {missing}")
    print(f"x ({xd['arm_x']} on {src_sep}): {len(log)} rebuilds")


def cmd_check_inputs():
    """Zero renders. Stage F: the held-out assertion (fail closed), the pool rule against the
    label table's stored S scores, the leak assertions (C′, and X's networks if added), the
    contexts', separations' and identity checks, the paired H/M rebuild checks and X's. Stage D:
    1c's and 1b's checks (and 1d's for X). Writes F/inputs.json; `search` refuses without ok."""
    import numpy as np

    from learn import di_fine_structure as DF
    from learn import local_objective_1d as LD
    from learn import rank_margin as RM
    from learn import song_settings as SS

    probs = {}
    held = heldout_check()
    if held:
        probs["heldout"] = held
    lt = lt_parts()
    step3 = set(d_parts())
    rule = pool_by_rule(lt, step3, lambda s: _load(K.HOME / "learn/label-table" / s / "menu.json"))
    if rule != pool_slugs():
        probs["pool_rule"] = {"by_rule_not_declared": sorted(set(rule) - set(pool_slugs())),
                              "declared_not_by_rule": sorted(set(pool_slugs()) - set(rule))}
    xd = _load(x_path())
    xd = xd["outcome"] if xd else None
    leak, x_probs = {}, {}
    fo = SS.folds()
    for slug in pool_slugs():
        band = lt[slug]["band"]
        f = fo.get(band)
        try:
            path = SS.cprime(f)
            cfg = _load(path.parent / "config.json") or {}
            caches = [pathlib.Path(c) for c in cfg.get("caches", [DF.MODELS / c for c in DF.CACHES])]
            DF.assert_no_leak(band, cfg.get("fold", f), f, DF.train_pool_bands(f, caches))
        except Exception as e:                                           # fail closed
            leak[slug] = repr(e)
        if xd and xd.get("arm_x"):
            try:
                LD.assert_sepnet_ok(band, LD.net_path(f), f)
            except Exception as e:                                       # fail closed, for X only
                x_probs.setdefault("leak", {})[slug] = repr(e)
    if leak:
        probs["leak"] = leak
    for name, p in (("contexts", fdir("contexts", "check.json")), ("sep_htdemucs", fdir("sep", "htdemucs", "check.json")),
                    ("sep_mega53", fdir("sep", "mega53", "check.json")),
                    ("identity_htdemucs", OUT / "identity" / "identity-htdemucs.json"),
                    ("identity_mega53", OUT / "identity" / "identity-mega53.json"),
                    ("rebuilt_htdemucs", fdir("rebuilt", "htdemucs", "check.json")),
                    ("rebuilt_mega53", fdir("rebuilt", "mega53", "check.json"))):
        if not (_load(p) or {}).get("ok"):
            probs[name] = "missing or not ok" if not p.exists() else _load(p).get("problems", "not ok")
    pairs = {}
    lh, lm = _load(fdir("rebuilt", "htdemucs", "rebuild-log.json")), _load(fdir("rebuilt", "mega53", "rebuild-log.json"))
    if lh and lm:
        for slug in pool_slugs():
            if slug not in lh or slug not in lm:
                pairs[slug] = ["a rebuild is missing"]
                continue
            a, b = np.load(rebuilt_path("F", "H", slug)), np.load(rebuilt_path("F", "M", slug))
            n = min(len(a), len(b))
            g = int(RM.gcc_lag(a[:n], b[:n]))
            pp = pair_problems(g, lh[slug]["lufs"], lm[slug]["lufs"])
            if pp:
                pairs[slug] = pp
    if pairs:
        probs["rebuild_pairs"] = pairs
    if xd and xd.get("arm_x"):
        lx = _load(fdir("rebuilt", "x", "rebuild-log.json"))
        src_log = lm if xd["source"] == "mega53" else lh
        src_arm = "M" if xd["source"] == "mega53" else "H"
        xp = {}
        if not (lx and src_log and (_load(fdir("rebuilt", "x", "check.json")) or {}).get("ok")):
            xp["_all"] = "X's stage-F rebuilds missing or not ok"
        else:
            for slug in pool_slugs():
                a, b = np.load(rebuilt_path("F", "X", slug)), np.load(rebuilt_path("F", src_arm, slug))
                n = min(len(a), len(b))
                p = x_pair_problems(int(RM.gcc_lag(a[:n], b[:n])), lx[slug]["lufs"], src_log[slug]["lufs"])
                if p:
                    xp[slug] = p
        if xp:
            x_probs["rebuilds"] = xp
    d_probs, d_scoped = stage_d_input_problems(xd)
    has_x = bool(xd and xd.get("arm_x"))
    rec = {"ok": not probs, "problems": probs, "x_ok": (not x_probs) if has_x else None, "x_problems": x_probs,
           "stage_D_problems": d_probs, "stage_D_arm_problems": d_scoped, "x": xd,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(fdir("inputs.json"), rec)
    print("stage F inputs (H, M, S):", "ok" if rec["ok"] else json.dumps(probs, indent=1, ensure_ascii=False)[:4000])
    if has_x:
        print("stage F inputs (X; a failure stops X only):", "ok" if not x_probs else x_probs)
    print("stage D inputs:", "ok" if not d_probs else d_probs, d_scoped or "")
    if probs:
        raise SystemExit(1)


def stage_d_input_problems(xd):
    """-> (problems that stop stage D: H's and M's inputs, {arm: problems that stop only T or X})."""
    p, scoped = [], {}
    if not C.sep_ok("mega53"):
        p.append("1c's Mega-53 separation checks")
    if not LO.rebuilds_ok("cprime_mega53"):
        p.append("cprime_mega53 rebuild checks")
    if not LO.rebuilds_ok("cprime_ref"):
        scoped["T"] = ["cprime_ref (1b) rebuild checks"]
    if xd and xd.get("arm_x") and not LO.rebuilds_ok(xd["arm_x"]):
        scoped["X"] = [f"{xd['arm_x']} (1d) rebuild checks"]
    return p, scoped


def stop_arm(stage, arm, why):
    """A T or X input that failed its checks: that arm stops in this stage (zero renders spent on it)."""
    if arm not in SCOPED_ARMS:
        raise SystemExit(why)
    if not arm_stop_path(stage, arm).exists():
        _save(arm_stop_path(stage, arm), {"why": why, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"arm {arm} stops in stage {stage}: {why}", flush=True)


# --- search --------------------------------------------------------------------------------------

def result_path(stage, arm, slug, amp, search):
    return OUT / stage / arm / slug / amp / f"{search}.json"


def warm_path(stage, arm, slug, amp):
    return OUT / stage / arm / slug / amp / "warm.json"


def s_path(slug, amp):
    return OUT / "F" / "S" / slug / f"{amp}.json"


def _done(p):
    r = _load(p)
    return bool(r) and r.get("status") == "done"


def stored_s_objective(key, slug, amp, half):
    """1c's, 1b's or 1d's float score of S at render time (the same function, lag −52, own mask
    with the C′ fallback): `renders/<di>/<part>/<amp>.json` S_float."""
    di, cfg = STORED_S[key]
    r = json.loads((LO.OUT / "renders" / di / slug / f"{amp}.json").read_text())
    return r["S_float"]["scores"][cfg][half]


def renderer():
    rr = K.Renderer()
    if rr.r.isolate is not True:
        raise SystemExit("the renderer is not isolating renders")
    return rr


def _sdict(x):
    return LO.sdict(x)


def _warm(rr, stage, arm, slug, amp, x32, sel, S, warmed):
    """One warm-up per (part, amp, arm) per process, counted in the group's warm.json."""
    if (arm, slug, amp) in warmed:
        return
    rr.render(x32, sel, S)
    p = warm_path(stage, arm, slug, amp)
    w = _load(p) or {"renders": 0, "warm_ups": 0}
    _save(p, {"renders": w["renders"] + 1, "warm_ups": w["warm_ups"] + 1})
    warmed.add((arm, slug, amp))


def run_direction(rr, ctx, stage, arm, slug, amp, search, held, xd, *, stem=None, rb=None, lag=OBJ_LAG, path=None,
                  s_lags=()):
    """The recipe on one direction through one arm's rebuild; the shrunk setting and the unshrunk
    best judged through the measure DI on both halves. The kept FLAC is the shrunk setting's render
    even when the output fell back to S (stage F keeps S's own render per part and amp).
    stem, rb, lag, path: amendment 2's oracle arm overrides the reference, the search DI, the
    objective's lag and the record's path (defaults: the arm's own). s_lags: amendment 3, the first
    evaluation (S) is also scored at these lags (no renders), stored as `s_lag_check`."""
    import numpy as np

    path = result_path(stage, arm, slug, amp, search) if path is None else path
    part, sel, S, di, di32, ref_wav = ctx["part"], ctx["sel"], ctx["S"], ctx["di"], ctx["di32"], ctx["ref"]
    stem = arm_reference(stage, arm, slug, part, xd) if stem is None else stem
    rb = np.load(rebuilt_path(stage, arm, slug, xd)) if rb is None else rb
    rb32 = rb.astype(np.float32)
    dims = K.space(amp, S)
    n0, counter, curve = rr.count, {"activity_fallback": 0}, []
    rec = {"stage": stage, "arm": arm, "slug": slug, "amp": amp, "search": search, "held": held, "lag": lag,
           "status": "running"}
    s_key = arm if arm in ("M", "T") else (f"X:{xd['source']}" if arm == "X" else None)

    def f(x):
        y = rr.render(rb32, sel, x)
        v, proxy = objective(stem, y, rb, search, lag)
        counter["activity_fallback"] += int(proxy)
        curve.append(v)
        if len(curve) == 1 and s_lags:
            rec["s_lag_check"] = {"lag": lag, "value": v,
                                  "at": {str(g): objective(stem, y, rb, search, g)[0] for g in s_lags}}
        if len(curve) == 1 and stage == "D" and s_key:                    # the first evaluation is S
            stored = stored_s_objective(s_key, slug, amp, search)
            dev = LO.deviation(v, stored)
            rec["s_check"] = {"value": v, "stored": stored, "dev": dev}
            if dev > TOL:
                breakage(path, {**rec, "renders": rr.count - n0},
                         f"{stage} {arm} {slug} {amp} {search}: S's objective {v} moved {dev:.4f} from the stored {stored}",
                         stage, arm)
        return v

    def probe(x):
        y = rr.render(rb32, sel, x)
        v, proxy = objective(stem, y, rb, search, lag)
        return peak_dbfs(y), v

    if K.key(dict(S)) != K.key(ctx["S_stored"]):
        raise SystemExit(f"{amp}: the live S differs from arm B's stored copy")
    res = recipe(dims, S, f, probe)
    y_shrunk = rr.render(di32, sel, res["shrunk_x"])
    j_shrunk = K.judge(ref_wav, y_shrunk, di, part["judge_lag"])
    j_best = K.judge(ref_wav, rr.render(di32, sel, res["best_x"]), di, part["judge_lag"])
    scale = save_kept_flac(path.with_name(f"{search}-shrunk.flac"), y_shrunk)
    rec.update(objective_curve=curve, objective_best=res["best_value"], evaluations=res["evaluations"],
               activity_fallback=counter["activity_fallback"], probe=res["probe"], fallback=res["fallback"],
               output="S" if res["fallback"] else "shrunk", judge_shrunk=j_shrunk, judge_best=j_best,
               kept_flac_scale=scale, renders=rr.count - n0, status="done",
               settings={"best": _sdict(res["best_x"]), "shrunk": _sdict(res["shrunk_x"]),
                         "output": _sdict(res["output_x"])})
    _save(path, rec)
    print(stage, arm, slug, amp, search, "held", round(j_shrunk[held], 4), "fallback" if res["fallback"] else "",
          rec["renders"], flush=True)


def run_h_check(rr, ctx, slug, amp, search, held):
    """Stage D's H: the stored 3-C′ shrink-0.5 setting rendered once through C′'s stem rebuild
    for the fallback rule; its judges are stored (`levers/early/`)."""
    import numpy as np

    from learn import song_settings as SS

    path = result_path("D", "H", slug, amp, search)
    rb = np.load(rebuilt_path("D", "H", slug))
    x = L._settings(L.OUT / "early" / "lever-shrink-0.5" / slug / amp / f"{search}.json")
    n0 = rr.count
    y = rr.render(rb.astype(np.float32), ctx["sel"], x)
    v, proxy = objective(SS.stem(slug), y, rb, search)
    why = fallback_reason(peak_dbfs(y), v)
    _save(path, {"stage": "D", "arm": "H", "slug": slug, "amp": amp, "search": search, "held": held,
                 "probe": {"peak_dbfs": peak_dbfs(y), "objective": v, "activity_fallback": proxy},
                 "fallback": why, "output": "S" if why else "shrunk", "renders": rr.count - n0, "status": "done"})


def group_ctx(menu, ms, stage, slug, amp):
    from learn import confirm_run as CR

    part = part_of(stage, slug)
    sel, S = menu[amp][K.START[part["gain_class"]][amp]]
    di = K.measure_di(part)
    return {"part": part, "sel": sel, "S": S, "S_stored": ms[amp][part["gain_class"]][1], "di": di,
            "di32": di.astype("float32"), "ref": CR.mono(part["crop"] / "reference.wav")}


def run_s_group(rr, ctx, slug, amp):
    """Stage F's S per (part, amp): a measure-DI warm-up and S's judge, checked against the label
    table's stored `flat` score within 0.005 on every half the judge scores (a miss stops)."""
    p = s_path(slug, amp)
    if _done(p):
        return
    n0 = rr.count
    rr.render(ctx["di32"], ctx["sel"], ctx["S"])                          # measure-DI warm-up
    y = rr.render(ctx["di32"], ctx["sel"], ctx["S"])
    j = K.judge(ctx["ref"], y, ctx["di"], ctx["part"]["judge_lag"])
    stored = json.loads((K.HOME / "learn/label-table" / slug / "menu.json").read_text())
    st = stored[amp][K.START[ctx["part"]["gain_class"]][amp]]["flat"]
    devs = {h: LO.deviation(j[h], st[h]) for h in ("A", "B")}
    scale = save_kept_flac(p.with_suffix(".flac"), y)
    rec = {"slug": slug, "amp": amp, "judge": j, "stored": st, "devs": devs, "renders": rr.count - n0,
           "kept_flac_scale": scale, "status": "done"}
    if max(devs.values()) > TOL:
        breakage(p, rec, f"F S {slug} {amp}: S's judge moved {max(devs.values()):.4f} from the label table's")
    _save(p, rec)


def run_repeat_check(rr, menu, ms, dirs):
    """Stage D: 6 directions by random.Random(20261034); H's stored shrunk setting through the
    measure DI must reproduce its stored held-half judge within 0.005."""
    p = OUT / "D" / "repeat.json"
    if _done(p):
        return
    n0, devs = rr.count, {}
    for slug, amp, search, held in repeat_draw(dirs):
        ctx = group_ctx(menu, ms, "D", slug, amp)
        rr.render(ctx["di32"], ctx["sel"], ctx["S"])                       # warm-up
        stored = json.loads((L.OUT / "early" / "lever-shrink-0.5" / slug / amp / f"{search}.json").read_text())
        x = L._settings(L.OUT / "early" / "lever-shrink-0.5" / slug / amp / f"{search}.json")
        j = K.judge(ctx["ref"], rr.render(ctx["di32"], ctx["sel"], x), ctx["di"], ctx["part"]["judge_lag"])
        devs[f"{slug}|{amp}|{search}"] = LO.deviation(j[held], stored["judge"][held])
    rec = {"draw": [list(d) for d in repeat_draw(dirs)], "devs": devs, "renders": rr.count - n0, "status": "done",
           "worst": max(devs.values())}
    if rec["worst"] > TOL:
        breakage(p, rec, f"D repeat check: the stored comparator moved {rec['worst']:.4f}")
    _save(p, rec)
    print("repeat check, worst |log|:", round(rec["worst"], 6), flush=True)


def planned_left(stage, dirs, live, xd):
    """Renders still to do for the whole stage (every shard), by the plan's per-direction counts."""
    n = 0
    for arm in live:
        todo = [d for d in dirs if not _done(result_path(stage, arm, *d[:3]))]
        n += len(todo) * (1 if (stage == "D" and arm == "H") else PER_DIRECTION) + len(groups(todo))
    if stage == "D" and not _done(OUT / "D" / "repeat.json"):
        n += 2 * REPEAT_N
    if stage == "F":
        n += 2 * sum(not _done(s_path(s, a)) for s, a in groups(dirs))
    return n


def cmd_search(stage, shard):
    """A stage's renders for one shard (groups of (part, amp)). Stage D, arm by arm (H's fallback
    checks, M, T, then X): the repeat check first (shard 0; the others wait for it). Stage F, group
    by group: S, then H, M (and X). Guards: the stop files, the render gate, the swap and disk
    guards, the stage's hard cap, the plumbing checks."""
    import numpy as np

    xd = x_decision()
    live = arms(stage, xd)
    dirs = stage_dirs(stage)
    if len(dirs) != N_DIRS[stage]:
        raise SystemExit(f"stage {stage}: {len(dirs)} directions, not the plan's {N_DIRS[stage]}")
    if stage == "F":
        require_heldout_ok()
        inp = _load(fdir("inputs.json")) or {}
        if not inp.get("ok"):
            raise SystemExit("run `check-inputs` first (stage F's inputs must pass)")
        if "X" in live and inp.get("x_ok") is not True:
            stop_arm("F", "X", f"X's stage-F inputs failed their checks: {inp.get('x_problems')}")
    else:
        bad, scoped = stage_d_input_problems(xd)
        if bad:
            raise SystemExit(f"stage D inputs not ready: {bad}")
        for arm, why in scoped.items():
            if arm in live:
                stop_arm("D", arm, f"inputs failed their checks: {why}")
    check_stop()
    why = cap_problem(spent(stage), planned_left(stage, dirs, live, xd), cap_of(stage, xd))
    if why:
        raise SystemExit(f"stage {stage}: {why}")
    if not disk_ok(planned_left(stage, dirs, live, xd) // 50):           # kept audio: about 1 FLAC per 50 renders
        raise SystemExit("free disk below the 31 GB guard")
    mine = set(shard_groups(dirs, shard))
    by_group = {}
    for dd in dirs:
        if (dd[0], dd[1]) in mine:
            by_group.setdefault((dd[0], dd[1]), []).append(dd)
    wait_render_gate()
    guard, ms = L.SwapGuard(), L.menu_S()
    rr = renderer()
    warmed = set()
    try:
        menu = rr.menu()
        if stage == "D":
            if shard[0] == 0:
                run_repeat_check(rr, menu, ms, dirs)
            t0 = time.time()
            while not _done(OUT / "D" / "repeat.json"):
                check_stop()
                if time.time() - t0 > REPEAT_WAIT_S:
                    raise SystemExit("shard 0's repeat check has not passed after 30 min: stopping (resumable)")
                print(time.strftime("%H:%M:%S"), "waiting for shard 0's repeat check", flush=True)
                time.sleep(POLL_S)
            order = [(arm, g) for arm in live for g in sorted(by_group)]
        else:
            order = [(arm, g) for g in sorted(by_group) for arm in ("S", *live)]
        for arm, (slug, amp) in order:
            if arm_stopped(stage, arm):
                continue
            todo = [dd for dd in by_group[(slug, amp)] if not _done(result_path(stage, arm, *dd[:3]))]
            if arm == "S":
                if _done(s_path(slug, amp)):
                    continue
            elif not todo:
                continue
            check_stop()
            guard.check()
            wait_render_gate()
            why = cap_problem(spent(stage), len(todo) * PER_DIRECTION + 2, cap_of(stage, xd))
            if why:
                raise SystemExit(f"stage {stage}: {why}")
            if not disk_ok(len(todo) + 1):
                raise SystemExit("free disk below the 31 GB guard (resumable)")
            failed = [dd for dd in todo if (_load(result_path(stage, arm, *dd[:3])) or {}).get("status") == "check_failed"]
            if failed:
                if arm in SCOPED_ARMS:
                    continue                                              # its stop file stands (or was cleared on purpose)
                raise SystemExit(f"{stage} {arm} {failed[0]} failed a check: investigate before rendering it again")
            ctx = group_ctx(menu, ms, stage, slug, amp)
            if arm == "S":
                run_s_group(rr, ctx, slug, amp)
                continue
            rb32 = np.load(rebuilt_path(stage, arm, slug, xd)).astype(np.float32)
            _warm(rr, stage, arm, slug, amp, rb32, ctx["sel"], ctx["S"], warmed)
            try:
                for slug_, amp_, search, held in todo:
                    check_stop()
                    if arm_stopped(stage, arm):
                        break
                    if stage == "D" and arm == "H":
                        run_h_check(rr, ctx, slug_, amp_, search, held)
                    else:
                        run_direction(rr, ctx, stage, arm, slug_, amp_, search, held, xd)
            except ArmStopped as e:                                       # T or X only; H, M and S go on
                print(time.strftime("%H:%M:%S"), str(e), flush=True)
    finally:
        rr.close()
    stopped = [a for a in live if arm_stopped(stage, a)]
    print(f"stage {stage} shard {shard[0]}/{shard[1]}: done; renders this process {rr.count}"
          + (f"; arms stopped by a failed check: {stopped}" if stopped else ""))


# --- the report ------------------------------------------------------------------------------------

def held_d(stage, arm, u, s_held):
    """An arm's held-half true-DI distance for a unit (the output: S's when it fell back), and the
    unshrunk best's. -> (d, d_unshrunk, record) or (None, None, None) if not done."""
    r = _load(result_path(stage, arm, u["slug"], u["amp"], u["search"]))
    if not r or r.get("status") != "done":
        return None, None, None
    if stage == "D" and arm == "H":
        lv = _load(L.OUT / "early" / "lever-shrink-0.5" / u["slug"] / u["amp"] / f"{u['search']}.json")
        best = _load(L.OUT / "early" / "C'" / u["slug"] / u["amp"] / f"{u['search']}.json")
        d = s_held if r.get("fallback") else lv["judge"][u["held"]]
        return d, best["judge"][u["held"]], r
    d = s_held if r.get("fallback") else r["judge_shrunk"][u["held"]]
    return d, r["judge_best"][u["held"]], r


def build_units(stage, live):
    """Units per direction: {slug, band, cls, amp, search, held, d: {S, H, M, ...}, rec}; S is step
    3's stored S judge (stage D) or the fresh one (stage F)."""
    if stage == "D":
        kept, _ = R.drop_refused(L.gathered_units())
        units = [{**{k: u[k] for k in ("slug", "band", "cls", "amp", "search", "held")}, "d": {"S": u["d"]["S"]}}
                 for u in kept]
    else:
        units = []
        for slug, amp, search, held in stage_dirs("F"):
            p = f_part(slug)
            s = _load(s_path(slug, amp))
            units.append({"slug": slug, "band": p["band"], "cls": p["gain_class"], "amp": amp, "search": search,
                          "held": held, "d": {"S": s["judge"][held] if s and s.get("status") == "done" else None}})
    for u in units:
        u["rec"] = {}
        for arm in live:
            d, du, r = held_d(stage, arm, u, u["d"]["S"])
            u["d"][arm], u["d"][f"{arm}_unshrunk"], u["rec"][arm] = d, du, r
    return units


def contrast_arms(a, b, xd=None):
    """The directions a contrast is read on (amendment 1, item 3): every contrast among S, H and M
    on the directions where all three score; a contrast with T or X on those and its own arm. So
    T and X never change a primary."""
    extra = tuple(x for x in (a, b) if x not in BASE and not x.endswith("_unshrunk"))
    own = tuple(x for x in (a, b) if x.endswith("_unshrunk"))
    return BASE + extra + own


def units_for(units, arms_):
    kept, dropped = R.drop_refused(units, methods=arms_)
    return kept, dropped


def row_filter(row, stage, bt, snr):
    """A unit filter for a row: 1c's rows (bleed rules by cell or direction, Cambridge only,
    without the MUSDB18-train bands) and this plan's (without any MUSDB18 song, SNR ≥ 1 dB, F-song)."""
    if row == "all":
        return lambda u: True
    if row in C.ROWS:
        return lambda u: u["search"] in C.kept_directions(row, u["slug"], u["band"], bt)
    if row == "without_any_musdb":
        return lambda u: u["band"] not in (*R.MUSDB_TRAIN_BANDS, *MUSDB_TEST_BANDS)
    if row == "snr_ge_1db":
        return lambda u: snr.get(u["slug"]) is not None and snr[u["slug"]] >= SNR_MIN_DB
    if row == "f_song":
        return lambda u: u["slug"] in F_SONG
    raise ValueError(row)


def rows_for(stage):
    return tuple(dict.fromkeys(("all", *C.ROWS, "without_any_musdb", "snr_ge_1db")
                               + (("f_song",) if stage == "F" else ())))


def log_rows(units, a, b):
    """{(slug, amp, search): (slug, band, cls, log(d_a / d_b))} where both are finite."""
    out = {}
    for u in units:
        x, y = u["d"].get(a), u["d"].get(b)
        if L.finite_pos(x) and L.finite_pos(y):
            out[(u["slug"], u["amp"], u["search"])] = (u["slug"], u["band"], u["cls"], math.log(x / y))
    return out


def contrast(units, a, b, rows, filters):
    """a − b (log of the held distances) on its own directions, on every row."""
    kept, dropped = units_for(units, contrast_arms(a, b))
    out = {"directions": len(kept), "dropped": [list(d) for d in dropped], "rows": {}}
    for row in rows:
        sel = [u for u in kept if filters[row](u)]
        out["rows"][row] = L.effects(sel, a, b) if sel else None
    return out


def share_of_t(units, rows, filters):
    """(M − H) / (T − H), band-weighted with Fieller's 90% interval (1c's `share`)."""
    kept, _ = units_for(units, contrast_arms("T", "M"))
    out = {}
    for row in rows:
        sel = [u for u in kept if filters[row](u)]
        num, den = log_rows(sel, "M", "H"), log_rows(sel, "T", "H")
        both = set(num) & set(den)
        out[row] = C.share({k: num[k] for k in both}, {k: den[k] for k in both}) if both else None
    return out


def complete(units, arms_, n_expected):
    """The fixed-set gate: every declared direction has every named arm's result (and S). -> None,
    or why a contrast on these arms is refused."""
    if len(units) != n_expected:
        return f"{len(units)} directions, not {n_expected}"
    miss = sum(1 for u in units for a in arms_ if u["d"].get(a) is None)
    return f"{miss} arm results missing" if miss else None


def contrasts_for(stage, xd):
    c = {"P_" + stage: ("M", "H"), "H_minus_S": ("H", "S"), "M_minus_S": ("M", "S"),
         "H_unshrunk_minus_H": ("H_unshrunk", "H"), "M_unshrunk_minus_M": ("M_unshrunk", "M")}
    if stage == "D":
        c.update({"T_minus_H": ("T", "H"), "T_minus_S": ("T", "S"), "M_minus_T": ("M", "T"),
                  "T_unshrunk_minus_T": ("T_unshrunk", "T")})
    if xd and xd.get("arm_x"):
        xa, xb = xd["contrast"]
        c.update({f"X_minus_{xb}": (xa, xb), "X_minus_S": ("X", "S"), "X_unshrunk_minus_X": ("X_unshrunk", "X")})
    return c


def snr_table(stage):
    """The label table's (stage F) or step 3's (stage D) htdemucs instrumental stem: gain-fitted SNR
    against reference.wav, dB (zero renders)."""
    from learn import confirm_run as CR
    from learn import label_table as LT
    from learn import song_settings as SS

    out = {}
    slugs = sorted(d_parts()) if stage == "D" else pool_slugs()
    for s in slugs:
        p = part_of(stage, s)
        ref = CR.mono(p["crop"] / "reference.wav")
        if stage == "D":
            stem = SS.stem(s)
        else:
            sp = LT.stem_path(s)
            stem = CR.mono(sp) if sp else None
        out[s] = C.snr_db(stem, ref) if stem is not None else None
    return out


def summarise(rep_c):
    a = (rep_c.get("rows") or {}).get("all") or {}
    s = a.get("all") or {}
    if s.get("band_weighted_mean") is None:
        return str(s.get("band_weighted_mean"))
    if s.get("lo90") is None:
        return f"{s['band_weighted_mean']:+.3f}"
    return f"{s['band_weighted_mean']:+.3f} [{s['lo90']:+.3f}, {s['hi90']:+.3f}] ({s['bands']} bands)"


def report_from_units(stage, units, live, xd, bt, snr):
    """The stage's report from its units (pure apart from the bleed table and SNRs passed in)."""
    rows = rows_for(stage)
    filters = {r: row_filter(r, stage, bt, snr) for r in rows}
    rep = {"stage": stage, "arms": list(live), "x": xd, "directions": len(units), "contrasts": {}, "complete": {}}
    for name, (a, b) in contrasts_for(stage, xd).items():
        arms_ = contrast_arms(a, b)
        why = complete(units, [x for x in arms_ if not x.endswith("_unshrunk")], N_DIRS[stage])
        rep["complete"][name] = why
        res = contrast(units, a, b, rows, filters)
        res["refused"] = why
        rep["contrasts"][name] = res
    if stage == "D":
        rep["share_M_of_T"] = share_of_t(units, rows, filters)
    prim = rep["contrasts"]["P_" + stage]
    rep["primary"] = {"name": "P_" + stage, "contrast": "M - H", "refused": prim["refused"],
                      "all": None if prim["refused"] else (prim["rows"]["all"] or {}).get("all")}
    rep["fallbacks"] = {a: sum(1 for u in units if (u["rec"].get(a) or {}).get("fallback")) for a in live}
    rep["activity_fallback"] = {a: [u["rec"][a].get("activity_fallback", 0) for u in units if u["rec"].get(a)]
                                for a in live if a != "H" or stage == "F"}
    rep["activity_fallback_total"] = {a: sum(v) for a, v in rep["activity_fallback"].items()}
    if stage == "D":
        rep["s_checks"] = {a: max((u["rec"][a]["s_check"]["dev"] for u in units
                                   if u["rec"].get(a) and "s_check" in u["rec"][a]), default=None)
                           for a in live if a != "H"}
    if stage == "F":
        per = {}
        for u in units:
            x, y = u["d"].get("M"), u["d"].get("H")
            if u["slug"] in F_BAND_PARTS and L.finite_pos(x) and L.finite_pos(y):
                per.setdefault(u["slug"], []).append(math.log(x / y))
        rep["f_band_parts_M_minus_H"] = {s: sum(v) / len(v) for s, v in per.items()}
    rep["snr_db_htdemucs_instrumental"] = snr
    return rep


def renders_used(stage):
    return spent(stage)


def cmd_report(stage):
    xd = x_decision()
    live = arms(stage, xd)
    units = build_units(stage, live)
    rep = report_from_units(stage, units, live, xd, C.load_bleed_table(), snr_table(stage))
    rep["renders_used"] = renders_used(stage)
    rep["renders_expected"] = expected_renders(stage, N_DIRS[stage], N_GROUPS[stage],
                                               [a for a in live if not (stage == "D" and a == "H")])
    rep["cap"] = cap_of(stage, xd)
    if stage == "D":
        rep["repeat_check"] = _load(OUT / "D" / "repeat.json")
    else:
        rep["s_judge_checks"] = max((v for s, a in groups(stage_dirs("F"))
                                     for v in ((_load(s_path(s, a)) or {}).get("devs") or {}).values()), default=None)
        rep["separation"] = {sep: _load(fdir("sep", sep, "log.json")) for sep in ("htdemucs", "mega53")}
        rep["inputs"] = _load(fdir("inputs.json"))
    _save(OUT / f"report-{stage}.json", rep)
    print(f"stage {stage}: {len(units)} directions; arms {live}; renders {rep['renders_used']} "
          f"(expected {rep['renders_expected']['total']}, cap {rep['cap']})")
    for name, c in rep["contrasts"].items():
        print(f"  {name:22s} {summarise(c)}" + (f"  REFUSED: {c['refused']}" if c["refused"] else ""))
    if stage == "D":
        print("  M's share of T's gain:", rep["share_M_of_T"].get("all"))
    print("  fallbacks:", rep["fallbacks"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("decide-x", "check-inputs", "contexts", "separate", "rebuild", "search", "report"))
    ap.add_argument("--sep", choices=("htdemucs", "mega53", "x"))
    ap.add_argument("--stage", choices=STAGES)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--identity-only", action="store_true",
                    help="rebuild: only the identity check on step 3's parts (lane A runs it first)")
    a = ap.parse_args(argv)
    sh = tuple(int(x) for x in a.shard.split("/"))
    if a.cmd in ("separate", "rebuild") and a.sep is None:
        ap.error(f"{a.cmd} needs --sep")
    if a.cmd == "separate" and a.sep == "x":
        ap.error("separate takes htdemucs or mega53")
    if a.cmd in ("search", "report") and a.stage is None:
        ap.error(f"{a.cmd} needs --stage")
    {"decide-x": cmd_decide_x, "check-inputs": cmd_check_inputs, "contexts": cmd_contexts,
     "separate": lambda: cmd_separate(a.sep),
     "rebuild": lambda: cmd_identity_only(a.sep) if a.identity_only else cmd_rebuild(a.sep),
     "search": lambda: cmd_search(a.stage, sh), "report": lambda: cmd_report(a.stage)}[a.cmd]()


if __name__ == "__main__":
    main()
