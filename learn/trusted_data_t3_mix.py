"""ROADMAP step (a), D_F5mix: F5's every-control model fed the mix (`docs/trusted-data-t0-design.md`, "D_F5mix: the
every-control model fed the mix"; ledger `trusted-data-t3`, amendment 3). Declared before any training; PENDING THE
USER'S YES (training longer than minutes). Outputs go to `trusted-data/t3-mix/` only; `t0/`, `t2/` and `t3/` are read,
never written.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    $MAIN -m learn.trusted_data_t3_mix check                        # zero renders: the frozen plan, the drift check
    $TORCH_PY -m learn.trusted_data_t3_mix train --arm D_F5mix|D_F5-noaug --seed 20261042|20261043   # 7-14 min each
    $TORCH_PY -m learn.trusted_data_t3_mix fit                      # the constant (D_F5's) and each arm's pull on FS5
    $TORCH_PY -m learn.trusted_data_t3_mix r0                       # zero renders: R0 per arm beside D_F5, paired
    $TORCH_PY -m learn.trusted_data_t3_mix vreal-predict            # zero renders
    $MAIN -u -m learn.trusted_data_t3_mix vreal-render --shard k/3  # 165 renders in all (33 groups x (1 + 2 x 2))
    $MAIN -m learn.trusted_data_t3_mix report                       # the rows against F5's stored renders

**The arms.** D_F5mix is D_F5 in everything but the input: the 115-control heads, the masked loss and the amp head;
F5's full twins (after F5's drops) and their labels; FS5 for early stopping and the fit; seeds 20261042 and 20261043;
the cap and patience; the readout and the pull rule. Its input is each full twin's stored self-built mix (`mix-t3`)
through `direct_stems`' D_mix input (the stem channel and the stem-loudness slot zero). D_stem's augmentations act on
the stem channel only, so D_F5mix trains unaugmented (as the pilot's D_mix). D_F5-noaug is D_F5 with augmentation off
(the stem input), so the input contrast D_F5mix - D_F5-noaug differs in the input alone. The constant is D_F5's.

**Frozen V-real-11.** T3's stored plan is read as frozen (no re-plan): F5's and FS5's examples and V-real-11. T0's
lists hash is recorded, not enforced; a drift check refuses instead unless every F5/FS5 example's DIs are still
verified and its section usable, and every V-real-11 member is still in today's membership (`lists_drift`).

**The readout.** First R0's rule on FS5 (zero renders, descriptive): each arm's table with D_F5 beside, paired per
head and in four summary rows. Then two answer sets, D_F5mix and D_F5-noaug, on V-real-11 (no stop rule), read
against each other and F5's stored D_F5, D_core5, S and the constant.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import time

from learn import full_space as F
from learn import trusted_data as T
from learn import trusted_data_t3 as T3
from learn import trusted_data_t3_r as R
from learn import verify_tracks as V

OUT_DIR = "t3-mix"                                   # trusted-data/t3-mix/: never under t3/
MIX_ARM = "D_F5mix"
NOAUG_ARM = "D_F5-noaug"                             # D_F5 with augmentation off: the input contrast's other arm
NEW_ARMS = (MIX_ARM, NOAUG_ARM)
INPUT_ARM = "Dmix"                                   # direct_stems' D_mix input: stem channel and its loudness slot 0
INPUT_OF = {MIX_ARM: INPUT_ARM, NOAUG_ARM: T.MODEL_ARM}   # D_F5-noaug: D_stem's input, as D_F5
LEDGER_KEY = "amendment_3"
LEDGER_MARK = "D_F5mix (ROADMAP (a))"
DESIGN = ("docs/trusted-data-t0-design.md#d_f5mix-the-every-control-model-fed-the-mix-roadmap-step-a-declared-"
          "2026-10-27-nothing-run")
STATUS = ("declared 2026-10-27 before any training (ledger trusted-data-t3, amendment 3); not post hoc for D_F5mix; "
          "V-real read again after F5 and R1")
INPUTS = {MIX_ARM: "the full twin's stored self-built mix (mix-t3) through direct_stems' D_mix input (the stem channel "
                   "and the stem-loudness slot zero); unaugmented, because D_stem's augmentations act on the stem "
                   "channel only",
          NOAUG_ARM: "the full twin's stored X-LANCE stem (xlance_g-t3) through D_F5's D_stem input; augmentation off"}
PAIRS = {"the input": (MIX_ARM, NOAUG_ARM),                          # primary: both unaugmented
         "input and augmentation": (MIX_ARM, T3.FULL),               # beside, descriptive
         "augmentation": (NOAUG_ARM, T3.FULL)}                       # beside, descriptive
RENDERS_PER_GROUP = 1 + 2 * len(NEW_ARMS)            # 1 priming at S + 2 arms x 2 directions
SUMMARY = ("knobs", "switches", "amp choice", "mics")
BETTER = {"knobs": "below", "switches": "above", "amp choice": "above", "mics": "above"}

_save, _load = V._save, V._load


# --- pure: the frozen plan under today's lists -------------------------------------------------------------------

def lists_drift(ids, frozen_members, t2_examples, tr, today_members):
    """What today's T0 lists change for the frozen step: examples (F5's and FS5's kept ids) whose target DI or an
    other guitar's DI is no longer verified, or whose section is no longer usable; frozen V-real members no longer in
    today's membership; members today's lists would add (printed, kept out). -> dict with "ok"."""
    verified, bad = T.verified_dis(tr), T.unusable(tr)
    ex = {x["i"]: x for x in t2_examples}
    stale = []
    for i in ids:
        x = ex.get(i)
        if x is None:
            stale.append((i, "not in T2's plan"))
        elif x["di"] not in verified:
            stale.append((i, "the target's DI is no longer verified"))
        elif x["section"] in bad:
            stale.append((i, "the section is no longer usable"))
        elif any(o["di"] not in verified for o in x.get("others") or []):
            stale.append((i, "an other guitar's DI is no longer verified"))
    today = set(today_members)
    lost = [m for m in frozen_members if m not in today]
    added = [m for m in today_members if m not in set(frozen_members)]
    return {"examples": len(ids), "stale": stale, "vreal_lost": lost, "vreal_added": added,
            "ok": not stale and not lost}


def canon(x):
    """A JSON form that compares NaN equal to NaN (the constants hold NaN where no label sounds)."""
    return json.dumps(x, sort_keys=True, default=str)


# --- pure: the paired FS5 read -------------------------------------------------------------------------------------

def jackknife(stat, groups):
    """A statistic with the delete-one-section jackknife's 90% t interval (sections - 1 df), as R0's AUC.
    stat(drop) -> float or None, with `drop` the left-out section (None: all). No interval with fewer than 2
    sections or a fold where the statistic is undefined. -> {point, lo, hi, sections}."""
    import numpy as np

    from learn import pretrain_set as PS

    secs = sorted(set(groups))
    p = stat(None)
    out = {"point": p, "lo": None, "hi": None, "sections": len(secs)}
    if p is None or len(secs) < 2:
        return out
    th = []
    for s in secs:
        v = stat(s)
        if v is None:
            return out
        th.append(v)
    th = np.asarray(th, np.float64)
    k = len(th)
    se = math.sqrt((k - 1) / k * float(((th - th.mean()) ** 2).sum()))
    h = PS.t90(k - 1) * se
    out.update(lo=p - h, hi=p + h)
    return out


def _auc_steps(per, drop):
    """[AUC_a - AUC_b] over switches `per` ([(y, qa, qb, groups)]) with section `drop` left out; None if any is
    undefined."""
    import numpy as np

    out = []
    for y, qa, qb, g in per:
        m = np.ones(len(y), bool) if drop is None else g != drop
        a, b = R.auc(y[m], qa[m]), R.auc(y[m], qb[m])
        if a is None or b is None:
            return None
        out.append(a - b)
    return out


def auc_step(y, qa, qb, groups):
    """AUC_a - AUC_b on the same examples, delete-one-section jackknife 90% t."""
    import numpy as np

    per = [(np.asarray(y, bool), np.asarray(qa, np.float64), np.asarray(qb, np.float64), np.asarray(groups))]

    def stat(drop):
        v = _auc_steps(per, drop)
        return None if v is None else v[0]
    return jackknife(stat, per[0][3].tolist())


def favours(better, s):
    """Which arm a paired step a - b's interval favours: "a", "b", or None (the interval holds 0)."""
    if s.get("lo") is None or s.get("hi") is None:
        return None
    if better == "below":
        return "a" if s["hi"] < 0 else ("b" if s["lo"] > 0 else None)
    return "a" if s["lo"] > 0 else ("b" if s["hi"] < 0 else None)


def _switch_data(ex_a, ex_b, j, sec):
    import numpy as np

    ids = [i for i, e in ex_a.items() if e["sm"][j] > 0]
    y = np.array([float(ex_a[i]["s"][j]) > 0.5 for i in ids], bool)
    return (y, np.array([float(ex_a[i]["sw_p"][j]) for i in ids]), np.array([float(ex_b[i]["sw_p"][j]) for i in ids]),
            np.array([sec[i] for i in ids]))


def _check_same(ex_a, ex_b):
    import numpy as np

    if set(ex_a) != set(ex_b):
        raise SystemExit("the two arms' FS5 examples differ")
    for i in ex_a:
        for k in ("c", "cm", "s", "sm", "k", "km"):
            if not np.array_equal(np.asarray(ex_a[i][k]), np.asarray(ex_b[i][k]), equal_nan=k == "c"):
                raise SystemExit(f"{i}: the two arms' labels differ ({k})")


def paired_rows(ex_a, ex_b, info):
    """Per head, arm a - arm b on the same FS5 examples (`trusted_data_t3_r.per_example`'s): knobs
    by the per-example E step |a - label| - |b - label| where the knob sounds (section-clustered 90% t; below 0
    favours a); switches by the AUC difference (jackknife; above 0 favours a); the mics and the amp by the accuracy
    difference (section-clustered; above 0 favours a). -> rows, one per head (116)."""
    import numpy as np

    _check_same(ex_a, ex_b)
    sec = {i: info[i]["section"] for i in ex_a}
    rows = []

    def row(name, kind, stat, n, better):
        rows.append({"name": name, "family": "amp_choice" if name == R.AMP_NAME else R.family_of_name(name),
                     "kind": kind, "n": n, "sections": stat["sections"], "point": stat["point"], "lo": stat["lo"],
                     "hi": stat["hi"], "better": better, "favours": favours(better, stat)})

    for j, n in enumerate(F.CONT):
        d = {i: abs(float(e["a2"][j]) - float(e["c"][j])) - abs(float(ex_b[i]["a2"][j]) - float(e["c"][j]))
             for i, e in ex_a.items() if e["cm"][j] > 0}
        row(n, "continuous", R.section_t(d, sec), len(d), "below")
    for j, n in enumerate(F.SW):
        y, qa, qb, g = _switch_data(ex_a, ex_b, j, sec)
        row(n, "switch", auc_step(y, qa, qb, g), len(y), "above")
    for j, n in enumerate(F.CAT):
        d = {i: float(int(np.argmax(e["mic_p"][j])) == int(e["k"][j]))
             - float(int(np.argmax(ex_b[i]["mic_p"][j])) == int(e["k"][j]))
             for i, e in ex_a.items() if e["km"][j] > 0}
        row(n, "accuracy", R.section_t(d, sec), len(d), "above")
    d = {i: float(int(np.argmax(e["amp_p"])) == F.AMPS.index(info[i]["amp"]))
         - float(int(np.argmax(ex_b[i]["amp_p"])) == F.AMPS.index(info[i]["amp"])) for i, e in ex_a.items()}
    row(R.AMP_NAME, "accuracy", R.section_t(d, sec), len(d), "above")
    return rows


def summary_rows(ex_a, ex_b, info):
    """The four summary rows, arm a - arm b, each with its 90% interval over FS5's sections: knobs, the per-example
    mean E step over sounding knobs (section-clustered t); switches, the mean AUC difference over the switches whose
    AUC difference is defined on all of FS5 and in every jackknife fold, so the row keeps its interval (those left out
    listed); the amp choice, the accuracy difference; the mics, the per-example mean accuracy difference over sounding
    mics. -> {name: {point, lo, hi, sections, n, better, favours}}."""
    import numpy as np

    _check_same(ex_a, ex_b)
    sec = {i: info[i]["section"] for i in ex_a}
    out = {}
    knobs = {}
    for i, e in ex_a.items():
        m = np.asarray(e["cm"]) > 0
        if m.any():
            c = np.asarray(e["c"], np.float64)
            knobs[i] = float(np.mean(np.abs(np.asarray(e["a2"], np.float64) - c)[m]
                                     - np.abs(np.asarray(ex_b[i]["a2"], np.float64) - c)[m]))
    out["knobs"] = {**R.section_t(knobs, sec), "n": len(knobs)}
    secs = sorted(set(sec.values()))
    per = {n: _switch_data(ex_a, ex_b, j, sec) for j, n in enumerate(F.SW)}
    use = [p for n, p in per.items() if all(_auc_steps([p], d) is not None for d in [None] + secs)]
    left = [n for n, p in per.items() if not any(p is q for q in use)]

    def stat(drop):
        v = _auc_steps(use, drop)
        return None if not v else float(np.mean(v))
    out["switches"] = {**jackknife(stat, secs), "n": len(use), "left_out": left}
    amp = {i: float(int(np.argmax(e["amp_p"])) == F.AMPS.index(info[i]["amp"]))
           - float(int(np.argmax(ex_b[i]["amp_p"])) == F.AMPS.index(info[i]["amp"])) for i, e in ex_a.items()}
    out["amp choice"] = {**R.section_t(amp, sec), "n": len(amp)}
    mics = {}
    for i, e in ex_a.items():
        v = [float(int(np.argmax(e["mic_p"][j])) == int(e["k"][j]))
             - float(int(np.argmax(ex_b[i]["mic_p"][j])) == int(e["k"][j]))
             for j in range(len(F.CAT)) if e["km"][j] > 0]
        if v:
            mics[i] = float(np.mean(v))
    out["mics"] = {**R.section_t(mics, sec), "n": len(mics)}
    for k, s in out.items():
        s["better"] = BETTER[k]
        s["favours"] = favours(BETTER[k], s)
    return out


def reliably_worse(s):
    """A summary row whose interval lies wholly on arm a's worse side."""
    return favours(s["better"], s) == "b"


def contrasts():
    """{name: (a, b)}: the primary (the input, both unaugmented), input and augmentation together, augmentation alone,
    the gate read with the mix input, S, the constant; F5's gate and R1 beside (stored)."""
    return {f"{MIX_ARM} - {NOAUG_ARM} (primary: the mix input, both unaugmented)": (MIX_ARM, NOAUG_ARM),
            f"{MIX_ARM} - {T3.FULL} (input and augmentation; descriptive)": (MIX_ARM, T3.FULL),
            f"{NOAUG_ARM} - {T3.FULL} (augmentation alone; descriptive)": (NOAUG_ARM, T3.FULL),
            f"{MIX_ARM} - {T3.CORE} (the gate read with the mix input)": (MIX_ARM, T3.CORE),
            f"{MIX_ARM} - S": (MIX_ARM, "S"),
            f"{MIX_ARM} - constant (D_F5's, rendered in F5)": (MIX_ARM, T3.CONST),
            f"F5: {T3.FULL} - {T3.CORE} (the gate, stored)": (T3.FULL, T3.CORE),
            f"R1: {R.R_ARM} - {T3.CORE} (stored)": (R.R_ARM, T3.CORE)}


def renders_needed(groups):
    return RENDERS_PER_GROUP * groups


# --- I/O -----------------------------------------------------------------------------------------------------------

def out_dir(root):
    return pathlib.Path(root) / OUT_DIR


def run_path(root, arm, seed):
    return out_dir(root) / "runs" / f"{arm}-{seed}.json"


def ledger_declared():
    d = json.loads((V.PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text())
    e = next((t for t in d["tests"] if t["test_id"] == T3.LEDGER_ID), {})
    return LEDGER_MARK in str(e.get(LEDGER_KEY, ""))


def require_mix(args):
    T3.require_t3(args)
    if not args.smoke and not ledger_declared():
        raise SystemExit(f"the ledger's {T3.LEDGER_ID} has no {LEDGER_KEY} declaring '{LEDGER_MARK}': real runs refuse")


def sha(path):
    import hashlib

    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def load_frozen(root, smoke=False):
    """T3's stored plan read as frozen (no re-plan), under the drift check in place of the lists hash.
    -> (plan, drift record)."""
    plan = _load(T.plan_path(root, T3.STAGE))
    if not plan or (plan.get("smoke") and not smoke):
        raise SystemExit("T3's stored plan (t3/plan.json) is missing")
    tr = T.load_lists(root, smoke)
    t2 = _load(T.plan_path(root, "t2"))
    if not t2:
        raise SystemExit("T2's plan is missing (t2/plan.json)")
    f5, fs, _, unbuilt = T3.t3_sets(root, plan)
    if unbuilt and not smoke:
        raise SystemExit(f"{len(unbuilt)} F5 or FS5 examples are not built")
    today = T3.vreal_membership(tr)["members"]
    drift = lists_drift(f5 + fs, plan["vreal"]["members"], t2["examples"], tr, today)
    drift.update(plan_lists_sha256=plan.get("lists_sha256"), today_lists_sha256=T.lists_sha(root),
                 frozen=plan["vreal"].get("name"), frozen_at=plan["vreal"].get("frozen"),
                 rule="T0's lists hash recorded, not enforced; the drift check refuses instead (amendment 3)")
    print(f"T3's frozen plan: {drift['frozen']} frozen {drift['frozen_at']}; T0's lists {str(drift['plan_lists_sha256'])[:12]} "
          f"then, {drift['today_lists_sha256'][:12]} now; {len(f5)} F5 + {len(fs)} FS5 examples checked", flush=True)
    for i, why in drift["stale"][:10]:
        print(f"  no longer trusted: {i} ({why})")
    for m in drift["vreal_lost"]:
        print(f"  frozen V-real member no longer in today's membership: {m}")
    for m in drift["vreal_added"]:
        print(f"  today's lists would add {m}: kept out (V-real is frozen)")
    if not drift["ok"] and not smoke:
        raise SystemExit("today's T0 lists remove something F5, FS5 or V-real-11 uses: the frozen step refuses")
    return plan, drift


def arm_data(arm, rows, files, encode):
    """An arm's training data: T2's `ArmData` on the full twins' files, unaugmented, read through the arm's input
    (D_F5mix: D_mix's; D_F5-noaug: D_stem's, as D_F5)."""
    data = T.ArmData(rows, files, aug=False, encode=encode)
    data.arm, data.aug = INPUT_OF[arm], False
    return data


def same_examples(ref, refused, n_train, n_es):
    """D_F5's run record against this run's examples: the same dropped ids and the same counts. -> why not, or None."""
    if sorted(ref.get("dropped") or []) != sorted(refused):
        return (f"the dropped ids differ from D_F5's ({len(ref.get('dropped') or [])} there, {len(refused)} here; "
                f"{len(set(ref.get('dropped') or []) ^ set(refused))} differ)")
    if (ref.get("train"), ref.get("early_stop")) != (n_train, n_es):
        return f"D_F5 trained on {ref.get('train')}/{ref.get('early_stop')} examples, here {n_train}/{n_es}"
    return None


def load_models(root, arm, smoke=False):
    import torch

    nets, recs = [], []
    for s in T3.TRAIN_SEEDS:
        rec = _load(run_path(root, arm, s))
        if not rec or (rec.get("smoke") and not smoke):
            raise SystemExit(f"{arm} seed {s} has no run")
        net = F.build_net()
        net.load_state_dict(torch.load(run_path(root, arm, s).with_suffix(".pt"), map_location="cpu"))
        net.eval()
        nets.append(net)
        recs.append(rec)
    return nets, recs


def model_shas(recs):
    return {str(r["seed"]): r["model_sha256"] for r in recs}


# --- check (MAIN; zero renders, writes nothing) ----------------------------------------------------------------------

def cmd_check(args):
    """The frozen plan and the drift check; every F5 and FS5 example's stored mix (`mix-t3`). Writes nothing."""
    require_mix(args)
    root = V.out_root(args)
    plan, drift = load_frozen(root, args.smoke)
    f5, fs, _, _ = T3.t3_sets(root, plan)
    missing = [i for i in f5 + fs if not T.ex_path(root, T3.STAGE, i, f"mix-{T3.STAGE}").exists()]
    print(f"stored full-twin mixes: {len(f5) + len(fs) - len(missing)} of {len(f5) + len(fs)} "
          f"({len(f5)} F5 + {len(fs)} FS5)")
    if missing and not args.smoke:
        raise SystemExit(f"{len(missing)} full twins have no stored mix-t3 features: {missing[:5]}")
    print(f"CHECK OK ({STATUS})")


# --- train, fit, r0 (TORCH_PY) ---------------------------------------------------------------------------------------

def cmd_train(args):
    """One run of a new arm: D_F5's recipe on F5's full twins with the arm's input, unaugmented; early stopping on
    FS5. Refuses unless its examples are D_F5's (the same dropped ids and counts)."""
    import numpy as np
    import torch

    from learn import direct_stems as DS
    from learn import pretrain_set as PS

    require_mix(args)
    root = V.out_root(args)
    if args.arm not in NEW_ARMS or (args.seed not in T3.TRAIN_SEEDS and not args.smoke):
        raise SystemExit(f"--arm in {NEW_ARMS}, --seed in {T3.TRAIN_SEEDS}")
    rp = run_path(root, args.arm, args.seed)
    if rp.exists():
        print(f"{rp.name} exists: nothing to do")
        return
    plan, drift = load_frozen(root, args.smoke)
    ok, pc = T3.positive_control(root, plan)
    if not ok and not args.smoke:
        raise SystemExit(f"F5's positive control has not passed: {pc}")
    _, _, refused, _ = T3.t3_sets(root, plan)
    ctx = DS.Ctx(quiet=True)
    tr_rows, es_rows = T3.arm_rows(root, ctx, plan, T3.FULL)
    why = same_examples(_load(T3.run_path(root, T3.FULL, args.seed)) or {}, refused, len(tr_rows), len(es_rows))
    if why and not args.smoke:
        raise SystemExit(f"{args.arm} must train on D_F5's examples: {why}")
    rows = tr_rows + es_rows
    files = {r["i"]: T3.files_of(root, T3.FULL, r["i"]) for r in rows}
    tr = np.arange(len(tr_rows))
    es = np.arange(len(tr_rows), len(rows))
    torch.set_num_threads(2)
    dev = torch.device("cpu" if os.environ.get("DS_DEVICE") == "cpu" or not torch.backends.mps.is_available()
                       else "mps")
    data = arm_data(args.arm, rows, files, T3.encode_for(T3.FULL))
    print(f"T3 {args.arm} seed {args.seed}: {len(tr)} train, {len(es)} early stopping (FS5); input: "
          f"{INPUTS[args.arm]}; {dev}", flush=True)
    t0 = time.time()
    for attempt in (1, 2):
        log = []
        data.masked, data.applied = 0, {}
        try:
            net, state, best_ep, best = DS.train_arm(data, tr, es, args.seed, dev, log, DS.MAX_EPOCHS,
                                                     build=F.build_net, loss=F.loss_fn)
            break
        except PS.StepsSkipped as e:
            print(f"attempt {attempt} aborted: {e}", flush=True)
            if dev.type == "mps":
                torch.mps.empty_cache()
            if attempt == 2:
                raise SystemExit(f"TRAIN FAILED {args.arm} {args.seed}: {e}")
    rp.parent.mkdir(parents=True, exist_ok=True)
    mp = rp.with_suffix(".pt")
    torch.save(state, mp)
    rec = {"plan": T.PLAN, "design": DESIGN, "stage": f"T3 {args.arm}", "status": STATUS, "arm": args.arm,
           "seed": args.seed, "input": INPUTS[args.arm], "model_arm": INPUT_OF[args.arm], "augmented": False,
           "labels": "115 (full space, masked; amp head)", "train": len(tr), "early_stop": len(es),
           "dropped": sorted(refused), "bands": sorted({r["band"] for r in tr_rows}), "attempts": attempt,
           "epochs_run": len(log), "best_epoch": best_ep, "best_early_stop_loss": best,
           "minutes": round((time.time() - t0) / 60, 1), "augmentations_applied": data.applied, "device": str(dev),
           "model": mp.name, "model_sha256": DS.hashlib_file(mp), "log": log, "drift": drift,
           "smoke": bool(args.smoke), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(rp, rec)
    print(f"TRAIN DONE {args.arm} {args.seed}: best epoch {best_ep} of {len(log)}")
    if best_ep is not None and best_ep >= DS.MAX_EPOCHS - T3.CAP_EDGE:
        print(f"WARNING: best epoch {best_ep} is within {T3.CAP_EDGE} of the cap {DS.MAX_EPOCHS}: extend this run "
              "before it is read")


def _fs5(root, plan, f5fit):
    """(training rows, FS5 rows, the 6-part full-space encoding, files) of the full twins; FS5 as F5's fit read it."""
    from learn import direct_stems as DS

    ctx = DS.Ctx(quiet=True)
    tr_rows, fs_rows = T3.arm_rows(root, ctx, plan, T3.FULL)
    if [r["i"] for r in fs_rows] != f5fit["fs5_ids"]:
        raise SystemExit("FS5 differs from the set F5's fit.json read")
    enc = T3.encode_for(T3.FULL)
    files = {r["i"]: T3.files_of(root, T3.FULL, r["i"]) for r in tr_rows + fs_rows}
    return tr_rows, fs_rows, (lambda lab: enc(lab)[:6]), files


def cmd_fit(args):
    """Per new arm (zero renders): the constant (refused unless it equals D_F5's stored one) and amendment 5's pull
    on FS5, with b refitted on FS5's two section folds (printed); the amp head's FS5 accuracy."""
    import numpy as np

    from learn import direct_sound_gate as G
    from learn import direct_stems as DS

    require_mix(args)
    root = V.out_root(args)
    plan, drift = load_frozen(root, args.smoke)
    f5fit = R.load_fit(root)
    fd = f5fit["models"][T3.FULL]
    tr_rows, fs_rows, enc6, files = _fs5(root, plan, f5fit)
    med = DS.label_medians(tr_rows, enc6)
    const = G.constant_answers(tr_rows, enc6, len(F.CONT), len(F.SW), len(F.CAT))
    if canon(DS.medians_json(med)) != canon(fd["constant"]) or \
            canon(G.const_json(const)) != canon(fd["constant_answers"]):
        if not args.smoke:
            raise SystemExit("the new arms' constant differs from D_F5's stored one: the labels are not D_F5's")
    cell_of = {r["i"]: (r["amp"], r["base"]) for r in fs_rows}
    folds = DS.section_folds(fs_rows)
    amp_of = {r["i"]: r["amp"] for r in fs_rows}
    models = {}
    for arm in NEW_ARMS:
        nets, recs = load_models(root, arm, args.smoke)
        X, C, Y, who = T3.fs_tensors(fs_rows, files, enc6, model_arm=INPUT_OF[arm])
        outs = F.run_nets(nets, X, C)
        _, ans = DS.median_answers(outs, who)
        lab = DS.labels_of(who, Y)
        table = DS.fit_pull_table(ans, lab, cell_of, med)
        fold_tables = {f: DS.fit_pull_table({i: a for i, a in ans.items() if folds[i] == f}, lab, cell_of, med)
                       for f in (0, 1)}
        amp_acc = [float(int(np.argmax(np.mean([F._softmax(o[n][5]) for o in outs], axis=0)))
                         == F.AMPS.index(amp_of[i])) for n, i in enumerate(who)]
        ent = {"models": model_shas(recs), "input": INPUTS[arm], "constant": DS.medians_json(med),
               "constant_answers": G.const_json(const), "constant_is_d_f5s": True, "pull": DS.table_json(table),
               "pull_summary": DS.pull_summary(table),
               "pull_folds": {str(f): DS.pull_summary(t) for f, t in fold_tables.items()},
               "fs5_examples": len(fs_rows), "fs5_sections": len({r["section"] for r in fs_rows}),
               "amp_head_fs_accuracy": float(np.mean(amp_acc)) if amp_acc else None}
        print(f"{arm}: pull {ent['pull_summary']}; folds {ent['pull_folds']}; amp head FS5 accuracy "
              f"{ent['amp_head_fs_accuracy']}", flush=True)
        models[arm] = ent
    _save(out_dir(root) / "fit.json", {"plan": T.PLAN, "design": DESIGN, "stage": "T3 D_F5mix fit", "status": STATUS,
                                       "readout_rule": DS.READOUT_RULE + " (T3's)", "fs5_ids": f5fit["fs5_ids"],
                                       "models": models, "drift": drift, "smoke": bool(args.smoke),
                                       "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print("FIT DONE t3-mix")


def load_fit(root, smoke=False):
    fit = _load(out_dir(root) / "fit.json")
    if not fit or (fit.get("smoke") and not smoke):
        raise SystemExit("run `fit` first")
    return fit


def print_r0(rec):
    for arm in NEW_ARMS:
        print(f"\n=== {arm} ===")
        R.print_r0(rec["rows"][arm])
    print(f"\nreadable heads (R0's rule; descriptive, no bar, about 6 per model by chance): "
          + ", ".join(f"{a} {n}" for a, n in rec["readable"].items()))
    print(f"beside, {T3.FULL} (R0, stored): " + ", ".join(f"{f} {c['readable']}/{c['heads']}"
                                                       for f, c in rec["by_family"][T3.FULL].items()))
    for name, (a, b) in PAIRS.items():
        p, sm = rec["paired"][name], rec["summary"][name]
        print(f"\n{a} - {b} ({name}{'; primary' if name == 'the input' else '; descriptive'}):")
        for who, arm in (("a", a), ("b", b)):
            names = [r["name"] for r in p if r["favours"] == who]
            print(f"  paired per head, reliably better for {arm}: {len(names)} {names}")
        for k in SUMMARY:
            s = sm[k]
            extra = f"; left out {s['left_out']}" if s.get("left_out") else ""
            print(f"  {k:12s} {s['point']} [{s['lo']}, {s['hi']}] ({s['better']} 0 favours {a}; n {s['n']}; "
                  f"favours {dict(a=a, b=b).get(s['favours'])}{extra})")


def cmd_r0(args):
    """Readout 1 (zero renders, descriptive): each new arm's R0 table on FS5 against the constant; D_F5's readout
    recomputed from its stored models (it must reproduce F5's stored R0 table); paired per head and the four summary
    rows for each pair (the input first). Read once: an existing r0.json is kept."""
    from learn import direct_sound_gate as G

    require_mix(args)
    root = V.out_root(args)
    op = out_dir(root) / "r0.json"
    if op.exists():
        print(f"{op} exists: read once (the table it holds is the declared one)")
        print_r0(_load(op))
        return
    plan, drift = load_frozen(root, args.smoke)
    f5fit, fit = R.load_fit(root), load_fit(root, args.smoke)
    r0_f5 = R.load_r0(root, args.smoke)
    tr_rows, fs_rows, enc6, files = _fs5(root, plan, f5fit)
    if fit["fs5_ids"] != f5fit["fs5_ids"]:
        raise SystemExit("the new arms' fit read another FS5")
    ex, shas = {}, {}
    for arm in NEW_ARMS + (T3.FULL,):
        if arm == T3.FULL:
            nets, recs = T3.load_models(root, T3.FULL, args.smoke)
            if not (f5fit["models"][T3.FULL]["models"] == model_shas(recs) == r0_f5["models"]):
                raise SystemExit("D_F5's models differ from those F5's fit and R0 read")
            model_arm = None
        else:
            nets, recs = load_models(root, arm, args.smoke)
            if fit["models"][arm]["models"] != model_shas(recs):
                raise SystemExit(f"{arm}: fit.json was made with other models")
            model_arm = INPUT_OF[arm]
        X, C, Y, who = T3.fs_tensors(fs_rows, files, enc6, model_arm=model_arm)
        ex[arm] = R.per_example(F.run_nets(nets, X, C), who, Y)
        shas[arm] = model_shas(recs)
    info = {r["i"]: {"section": r["section"], "cell": (r["amp"], r["base"]), "amp": r["amp"]} for r in fs_rows}
    rates, majority = R.train_priors([enc6(r["label"]) for r in tr_rows], [r["amp"] for r in tr_rows])
    const = G.const_from_json(f5fit["models"][T3.FULL]["constant_answers"])     # the new arms' constant is D_F5's
    rows = {arm: R.r0_rows(ex[arm], info, const, rates, majority) for arm in ex}
    stored = {r["name"] for r in r0_f5["rows"] if r["readable"]}
    again = {r["name"] for r in rows[T3.FULL] if r["readable"]}
    if again != stored and not args.smoke:
        raise SystemExit(f"D_F5's R0 does not reproduce F5's stored table: {sorted(again ^ stored)}")
    rec = {"plan": T.PLAN, "design": DESIGN, "stage": "T3 D_F5mix R0", "status": STATUS,
           "rule": "R0's: readable iff the 90% interval excludes chance in the right direction",
           "reading": "descriptive: no stop rule, V-real runs whatever FS5 shows; readable counts have no bar",
           "pairs": {k: list(v) for k, v in PAIRS.items()}, "models": shas,
           "fs5_examples": len(ex[MIX_ARM]), "fs5_sections": len({v["section"] for v in info.values()}),
           "rows": rows, "by_family": {a: R.by_family(r) for a, r in rows.items()},
           "readable": {a: sum(x["readable"] for x in r) for a, r in rows.items()},
           "paired": {k: paired_rows(ex[a], ex[b], info) for k, (a, b) in PAIRS.items()},
           "summary": {k: summary_rows(ex[a], ex[b], info) for k, (a, b) in PAIRS.items()},
           "drift": drift, "smoke": bool(args.smoke), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(op, rec)
    print_r0(rec)
    print(f"R0 DONE: {op}")


def load_r0(root, smoke=False):
    r0 = _load(out_dir(root) / "r0.json")
    if not r0 or (r0.get("smoke") and not smoke):
        raise SystemExit("run `r0` first")
    return r0


# --- V-real (predict: TORCH_PY, zero renders; render: MAIN) --------------------------------------------------------

def vreal_input(slug, info, man, target):
    """A part's V-real inputs as F5's `vreal-predict` read them: the crop's mix and its stored stem (the stem is read
    for the output-gain fit alone), one gain to the training median. -> dict with the hashes F5 recorded."""
    from learn import direct_existing as DE
    from learn import direct_stems as DS

    if info["kind"] == "stagef":
        mix, _, hashes = DE.f_inputs(slug, "mega53")
        return {"mix": mix, "stem": DS.stored_stem(man, f"stagef/{slug}"), "gain_db": DE.inference_gain_db(mix, target),
                "hashes": {"context": hashes["context"], "stem": man["stems"][f"stagef/{slug}"]["sha256"]}}
    from learn import confirm_run as CR

    mix = CR.mono(pathlib.Path(info["crop"]) / "mix.wav")
    return {"mix": mix, "stem": T3.crop_stem(info), "gain_db": DE.inference_gain_db(mix, target),
            "hashes": {"crop_record": info["record_sha256"], "stem": info["stem"]["sha256"]}}


def f5_predictions(root, plan, smoke=False):
    pp = T.stage_root(root, T3.STAGE) / "vreal" / "predictions.json"
    pred = _load(pp)
    if not pred or (pred.get("smoke") and not smoke):
        raise SystemExit("F5's V-real predictions are missing")
    if pred["members"] != plan["vreal"]["members"]:
        raise SystemExit("F5's predictions were made for another V-real membership")
    return pred, pp


def cmd_vreal_predict(args):
    """The new arms' answers on the frozen V-real-11 (zero renders): the crop's inputs through F5's step-4 path (input
    hashes equal to F5's), D_F5mix through D_mix's input and D_F5-noaug through D_stem's, each pulled by its own FS5
    fit, the plain readout; each arm's own amp recorded. Output gain stays S's here and is fitted at render."""
    from learn import arm_a_mega53 as A
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import local_objective as LO

    require_mix(args)
    root = V.out_root(args)
    plan, drift = load_frozen(root, args.smoke)
    r0 = load_r0(root, args.smoke)                       # read first (descriptive); no stop rule
    fit = load_fit(root, args.smoke)
    models = {}
    for arm in NEW_ARMS:
        nets, recs = load_models(root, arm, args.smoke)
        f = fit["models"][arm]
        if f["models"] != model_shas(recs) or r0["models"][arm] != model_shas(recs):
            raise SystemExit(f"{arm}: the fit or R0 was made with other models")
        models[arm] = (nets, model_shas(recs), DS.medians_from_json(f["constant"]), DS.table_from_json(f["pull"]))
    f5pred, f5pp = f5_predictions(root, plan, args.smoke)
    dirs, parts, dropped = T3.vreal_dirs(root, plan, bool(f5pred.get("dropped_members")))
    if sorted(dropped) != sorted(f5pred.get("dropped_members") or []):
        raise SystemExit("V-real's parts changed since F5's predictions")
    man = DS._load(DS.stems_manifest_path(DS.ROOT, T.SEP))
    target = json.loads(DE.LEVELS.read_text())["summary"]["eval_mix_lufs_median"]
    ms = A.L.menu_S()
    preds, own, inputs, gaps = {a: {} for a in NEW_ARMS}, {a: {} for a in NEW_ARMS}, {}, {}
    for slug, amp, search, held in dirs:
        cls, _ = T3.part_info(slug, parts[slug])
        if slug not in inputs:
            inputs[slug] = vreal_input(slug, parts[slug], man, target)
            if inputs[slug]["hashes"] != f5pred["inputs"].get(slug) and not args.smoke:
                raise SystemExit(f"{slug}: its inputs differ from those F5's predictions read")
        it = inputs[slug]
        s8, m8, ls, lm = DS.step4_half(it["stem"], it["mix"], search, it["gain_db"])
        _, S = ms[amp][cls]
        key = f"{slug}|{amp}|{search}"
        for arm, (nets, _, med, table) in models.items():
            x, c = DS.model_input(s8, m8, ls, lm, search, amp, cls, INPUT_OF[arm])
            b, gap = DS.cell_b(table, (amp, cls), F.cell_masks(amp)[0])
            if gap:
                gaps[f"{arm}|{amp}|{cls}"] = gap
            r = F.readout([o[0] for o in F.run_nets(nets, [x], [c])])
            diag = {"a2": [float(v) for v in r["a2"]], "sw_p": [float(v) for v in r["sw_p"]], "mics": r["mics"]}
            preds[arm][key] = {"settings": LO.sdict(T3.full_answer(amp, S, r, med[(amp, cls)], b)), "held": held,
                               "diag": diag}
            own[arm][f"{slug}|{search}"] = {"amp": r["amp"], "p": r["amp_p"]}
    od = out_dir(root) / "vreal"
    _save(od / "predictions.json", {
        "plan": T.PLAN, "design": DESIGN, "stage": "T3 D_F5mix V-real", "status": STATUS, "arms": list(NEW_ARMS),
        "input": INPUTS, "smoke": bool(args.smoke), "members": plan["vreal"]["members"], "dropped_members": dropped,
        "directions": len(dirs), "predictions": preds, "own_amp": own, "pull_gaps": gaps,
        "inputs": {s: v["hashes"] for s, v in inputs.items()}, "models": {a: m[1] for a, m in models.items()},
        "r0_sha256": sha(out_dir(root) / "r0.json"), "f5_predictions_sha256": sha(f5pp), "drift": drift,
        "output_gain": "S's here; fitted per answer at render to the stem's loudness, as F5 (" + F.OUTPUT_FIT_STATUS + ")",
        "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    groups = len({(s, a) for s, a, _, _ in dirs})
    print(f"MIX PREDICT: {len(dirs)} directions x {len(NEW_ARMS)} arms; {groups} groups, {renders_needed(groups)} renders to come"
          + (f"; dims with no fitted pull (read at the constant) {gaps}" if gaps else ""))


def cmd_vreal_render(args):
    """The new arms' V-real renders for one shard of (part, amp) groups: one discarded priming render at S, then each
    arm's answer once per direction, judged on both halves; output gain fitted to the stem's loudness and its |LUFS error|
    recorded (as F5). isolate=True; at most 3 render processes machine-wide; the 31 GB disk guard; a done group is
    kept."""
    from learn import arm_a_mega53 as A
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS

    require_mix(args)
    root = V.out_root(args)
    plan, _ = load_frozen(root, args.smoke)
    od = out_dir(root) / "vreal"
    pred = _load(od / "predictions.json")
    if not pred or (pred.get("smoke") and not args.smoke):
        raise SystemExit("run `vreal-predict` first")
    if pred["members"] != plan["vreal"]["members"]:
        raise SystemExit("the new arms' predictions were made for another V-real membership")
    if pred["r0_sha256"] != sha(out_dir(root) / "r0.json"):
        raise SystemExit("r0.json changed since vreal-predict")
    dirs, parts, dropped = T3.vreal_dirs(root, plan, bool(pred.get("dropped_members")))
    if sorted(dropped) != sorted(pred.get("dropped_members") or []):
        raise SystemExit("V-real's parts changed since vreal-predict")
    if PS.free_gb() < T.DISK_GUARD_GB:
        raise SystemExit(f"free disk below {T.DISK_GUARD_GB:.0f} GB")
    man = DS._load(DS.stems_manifest_path(DS.ROOT, T.SEP))
    mine = DE.shard(A.groups(dirs), args.shard)
    LO._wait_cap()
    DS.wait_render_slot()
    rr = A.renderer()
    ms = A.L.menu_S()
    try:
        menu = rr.menu()
        for slug, amp in mine:
            gp = od / "groups" / f"{slug}|{amp}.json"
            if (_load(gp) or {}).get("status") == "done":
                continue
            if PS.free_gb() < T.DISK_GUARD_GB:
                raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
            info = parts[slug]
            ctx = (A.group_ctx(menu, ms, "F", slug, amp) if info["kind"] == "stagef"
                   else T3.t3_group_ctx(menu, ms, info, amp))
            if K.key(dict(ctx["S"])) != K.key(ctx["S_stored"]):
                raise SystemExit(f"{amp}: the live S differs from the stored copy")
            g = {"sel": ctx["sel"], "S": ctx["S"], "di": ctx["di"], "di32": ctx["di32"], "ref": ctx["ref"],
                 "lag": ctx["part"]["judge_lag"]}
            stem = DS.stored_stem(man, f"stagef/{slug}") if info["kind"] == "stagef" else T3.crop_stem(info)
            settings = {a: {sh: LO.tdict(pred["predictions"][a][f"{slug}|{amp}|{sh}"]["settings"])
                            for sh, _ in K.DIRECTIONS} for a in NEW_ARMS}
            held_of = dict(K.DIRECTIONS)
            checks = {}

            def keep(arm, search, y, settings=settings, stem=stem, ref=g["ref"], checks=checks):
                gain = float(settings[arm][search].get(F.OUTPUT, "0"))
                checks[f"{arm}|{search}"] = T3.lufs_check(gain, y, stem, ref, search, held_of[search])

            rec = DS.run_group(rr, g, settings, False, None, K.judge, keep=keep, arms=NEW_ARMS)
            rec.update(slug=slug, amp=amp, lufs=checks, output_gain_fit=F.OUTPUT_FIT_STATUS, status_mix=STATUS)
            _save(gp, rec)
            print(slug, amp, rec["renders"], flush=True)
    finally:
        rr.close()
    print(f"MIX RENDER DONE {args.shard[0]}/{args.shard[1]}; renders {rr.count}")


def cmd_report(args):
    """The rows: D_F5mix - D_F5-noaug (primary), D_F5mix - D_F5 and D_F5-noaug - D_F5 (descriptive), D_F5mix -
    D_core5, - S, - the constant (F5's stored renders); F5's gate and R1 beside. Band-weighted, 90% band-clustered t (7 bands), per class and V-real-10 beside."""
    from learn import arm_a_mega53 as A
    from learn import direct_stems as DS
    from learn import perfect_sep_arm as P

    require_mix(args)
    root = V.out_root(args)
    plan, drift = load_frozen(root, args.smoke)
    od = out_dir(root) / "vreal"
    f5d = T.stage_root(root, T3.STAGE) / "vreal"
    rd = R.out_dir(root)
    pred, _ = f5_predictions(root, plan, args.smoke)
    members = set(plan["vreal"]["members"]) - set(pred.get("dropped_members") or [])
    v10 = set(plan["vreal"]["v_real_10"])
    crops = (_load(T3.crops_manifest_path(root)) or {}).get("crops") or {}
    parts, _ = T3.vreal_parts(sorted(members), A.pool_slugs(), crops, drop_missing=True)
    units = [u for u in P.build_units() if u["slug"] in members] + T3.t3_units(parts, f5d / "groups")
    cache = {}
    where = {MIX_ARM: od, NOAUG_ARM: od, R.R_ARM: rd}

    def value(arm):
        def f(u):
            d = where.get(arm, f5d)
            ck = (str(d), u["slug"], u["amp"])
            if ck not in cache:
                cache[ck] = _load(d / "groups" / f"{u['slug']}|{u['amp']}.json") or {}
            gr = cache[ck]
            if gr.get("status") != "done":
                return None
            return ((gr.get("judge") or {}).get(f"{arm}|{u['search']}") or {}).get(u["held"])
        return f

    arms = sorted({a for pair in contrasts().values() for a in pair} - {"S"})
    refused = {a: DS.add_step4_arm(units, a, value(a)) for a in arms}
    gaps = [f"{n} directions have no {a} value" for a in arms if (n := sum(1 for u in units if u["d"].get(a) is None))]
    bad = {a: n for a, n in refused.items() if n}
    if bad:
        gaps.append(f"refused answers scored as S {bad}")
    rows_ = ("all", "v_real_10")
    filt = {"all": lambda u: True, "v_real_10": lambda u: u["slug"] in v10}
    con = {name: DS.step4_contrast(units, a, b, filt, rows=rows_, fixed=("S",)) for name, (a, b) in contrasts().items()}
    lufs = []
    for (d, *_), gr in cache.items():
        if d == str(od):
            lufs += list((gr.get("lufs") or {}).values())
    renders = sum((_load(p) or {}).get("renders", 0) for p in (od / "groups").glob("*.json"))
    mp = _load(od / "predictions.json") or {}
    rep = {"plan": T.PLAN, "design": DESIGN, "stage": "T3 D_F5mix report", "status": STATUS,
           "v_real": sorted(members), "directions": len(units), "complete": not gaps, "incomplete_because": gaps,
           "refused_scored_as_S": refused, "contrasts": con, "abs_lufs_error": T3.lufs_summary(lufs),
           "own_amp": mp.get("own_amp"), "renders": renders, "drift": drift,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(out_dir(root) / "report.json", rep)
    print(f"T3 {MIX_ARM} and {NOAUG_ARM} ({STATUS}): V-real {len(members)} parts ({len(units)} directions); renders {renders}")
    for g in gaps:
        print(f"  incomplete: {g}")
    for name, c in con.items():
        for row in rows_:
            r = c["rows"].get(row) or {}
            for cls, s in [("", r.get("all") or {})] + sorted((r.get("per_class") or {}).items()):
                sign = f"; bands -/+ {s.get('bands_negative')}/{s.get('bands_positive')}" if s.get("bands") else ""
                print(f"  {name if not cls and row == 'all' else '':64s} {(row + ' ' + cls).strip():18s} "
                      f"{s.get('band_weighted_mean')} [{s.get('lo90')}, {s.get('hi90')}] ({s.get('bands')} bands{sign}) "
                      f"{T3.rule_reading(s)}")
    print(f"|LUFS error| (a pipeline check): {rep['abs_lufs_error']}")
    print("MIX REPORT DONE")


# --- main -----------------------------------------------------------------------------------------------------------

COMMANDS = {"check": cmd_check, "train": cmd_train, "fit": cmd_fit, "r0": cmd_r0, "vreal-predict": cmd_vreal_predict,
            "vreal-render": cmd_vreal_render, "report": cmd_report}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="trusted_data_t3_mix", description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=tuple(COMMANDS))
    ap.add_argument("--arm", default=None, choices=NEW_ARMS)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--shard", type=V.parse_shard, default=(0, 1))
    ap.add_argument("--out", default=None)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args(argv)
    if args.shard != (0, 1) and args.cmd != "vreal-render":
        raise SystemExit("--shard is for vreal-render")
    if (args.seed is None or args.arm is None) == (args.cmd == "train") or \
            (args.cmd != "train" and (args.seed, args.arm) != (None, None)):
        raise SystemExit("--arm and --seed are for train, and train needs both")
    return COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
