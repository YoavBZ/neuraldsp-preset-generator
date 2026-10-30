"""Step 3's V-real readout for the clean/crunch pool's arms (`docs/clean-crunch-pool-plan.md`, step 3; ledger
`trusted-data-t3`, amendment 6 and `amendment_6_readout`): each new arm is fitted, answers on the frozen V-real-11 and
is rendered and read against F5's stored D_F5 exactly as T3 read D_F5 (`trusted_data_t3`'s fit, vreal-predict,
vreal-render and report; `trusted_data_t3_mix`'s pattern for an arm read against F5's stored renders). Outputs go to
`trusted-data/cc-readout/<arm>/` only; `t2/`, `t3/` and the arms' own folders are read, never written.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    $TORCH_PY -m learn.cc_readout fit --arm D_F5bk                    # zero renders: the constant and the pull
    $TORCH_PY -m learn.cc_readout vreal-predict --arm D_F5bk          # zero renders
    $MAIN -u -m learn.cc_readout vreal-render --arm D_F5bk --shard k/3   # 165 renders (33 groups x (1 + 2 x 2))
    $MAIN -m learn.cc_readout report --arm D_F5bk                     # the rows against F5's stored renders

**The arms.** An arm is registered in `ARMS` with where its two runs are, its fit set (rows and feature files) and
whether its constant must be D_F5's. D_F5bk (`trusted_data_t3_bk`) is registered: its runs, FS5 remixed under step 1's
backings (`trusted_data_t3_bk.files_for`), D_F5's labels, so its constant must equal D_F5's stored one. D_CC registers
from `cc_build` (its pool, its own fit set FS_CC drawn from the new pool, its own constant; the "- constant" row stays
D_F5's stored constant, descriptive).

**The answers** (the plan's declared readout): per direction the arm's pulled answer (both seeds, as D_F5's) and the
same answer with the time-effect and spring heads at S (`full_space.FAMILIES["time effects and spring"]`), the
co-primary. V-real-11's inputs are the stored crop and its stock X-LANCE stem, exactly as F5's predictions read them
(hash-checked): the backing fix acts on training only.

**The rows** (band-weighted log ratios, 90% band-clustered t, per class with bands -/+, V-real-10 beside):
arm - D_F5 (primary); arm:at-S:time effects and spring - D_F5:at-S:time effects and spring (co-primary; F5 rendered
D_F5's family answer); arm - D_core5, - S, - constant (descriptive). No pass bar: effect sizes, an interval holding 0
is undecided.

Every Morgan render is isolate=True with one discarded priming render at S per (part, amp) group and the first 0.25 s
trimmed (`direct_stems.run_group`); at most 3 render processes machine-wide (`local_objective.RENDERS`); the 31 GB disk
guard.

**D_CC's follow-ups** (ledger `clean-crunch-pool-dcc`, `amendment_4`; approved by the user 2026-10-30), written to
`cc-readout/D_CC/followups/` only; step 3's files are read, never written:

    $TORCH_PY -m learn.cc_readout followup-predict --arm D_CC                # zero renders
    $MAIN -u -m learn.cc_readout followup-render --arm D_CC --shard k/3      # 165 renders (33 groups x (1 + 2 x 2))
    $MAIN -m learn.cc_readout followup-report --arm D_CC

(a) Each seed's own answer (`trusted_data_t3.full_answer` with `seed=`, as F5's D_F5:s<seed>), not rendered: the drive
switches, inputGain and the amp head per seed beside the pooled answer and D_F5's stored per-seed answers
(`drive_summary`); step 3's two answers are recomputed first and must equal the stored ones. (b) Two rendered answers:
the arm with the pedal family at S (`full_space.FAMILIES["pedals"]`, as F5's D_F5:at-S:pedals) and the arm's own
constant (`trusted_data_t3.constant_full` of the constant `fit` stored from the arm's training labels, the way T3's
`fit` made D_F5's), read against step 3's stored D_CC renders and F5's stored renders (`followup_contrasts`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import time

from learn import full_space as F
from learn import trusted_data as T
from learn import trusted_data_t3 as T3
from learn import verify_tracks as V

OUT_DIR = "cc-readout"                              # trusted-data/cc-readout/<arm>/
TIME_FAMILY = "time effects and spring"
LEDGER_KEY = "amendment_6_readout"
LEDGER_MARK = "clean/crunch pool step 3 readout"
PLAN = "docs/clean-crunch-pool-plan.md"
ANSWERS_PER_ARM = 2                                 # the arm, and the arm with the time-effect heads at S
RENDERS_PER_GROUP = 1 + ANSWERS_PER_ARM * 2         # 1 priming at S + 2 answers x 2 directions
FOLLOWUP_LEDGER_ID = "clean-crunch-pool-dcc"        # cc_build.LEDGER_ID (not imported: the light CI)
FOLLOWUP_KEY = "amendment_4"
FOLLOWUP_MARK = "D_CC follow-ups"
FOLLOWUP_DIR = "followups"                          # cc-readout/<arm>/followups/
FOLLOWUP_ARMS = ("D_CC",)
PEDALS = "pedals"
FOLLOWUP_ANSWERS = 2                                # pedals at S and the arm's own constant (per seed: not rendered)
FOLLOWUP_RENDERS_PER_GROUP = 1 + FOLLOWUP_ANSWERS * 2
DRIVES = ("drive1/drive1Active", "drive2/drive2Active")
INPUT_GAIN = "parameters/inputGain"
SELECTIONS = {"pr12 crunch": lambda amp, cls: amp == "pr12" and cls == "crunch",
              "crunch": lambda amp, cls: cls == "crunch", "all": lambda amp, cls: True}
RUNAWAY_FEEDBACK = 0.75                             # the runaway scan's pattern: the delay on at this feedback or more

_save, _load = V._save, V._load


# --- the arms --------------------------------------------------------------------------------------------------------

def _bk_runs(root, seed):
    from learn import trusted_data_t3_bk as BK

    return BK.run_path(root, seed)


def _bk_fit_rows(root, ctx, plan, smoke=False):
    """D_F5bk's (training rows, FS5 rows, files): D_F5's rows (the full twins, their labels) with the remixed
    features (`trusted_data_t3_bk.files_for`)."""
    from learn import trusted_data_t3_bk as BK

    p = BK.load_bk_plan(root, smoke)
    ent = {e["i"]: e for e in p["examples"]}
    tr_rows, fs_rows = T3.arm_rows(root, ctx, plan, T3.FULL)
    if [r["i"] for r in tr_rows] != p["f5"] or [r["i"] for r in fs_rows] != p["fs5"]:
        raise SystemExit("D_F5bk: the F5/FS5 examples differ from its plan")
    return tr_rows, fs_rows, {r["i"]: BK.files_for(ent[r["i"]], root) for r in tr_rows + fs_rows}


def _cc_runs(root, seed):
    from learn import cc_build as CB

    return CB.run_path(root, seed)


def _cc_fit_rows(root, ctx, plan, smoke=False):
    """D_CC's (training rows, FS_CC rows, files): its own pool (`cc_build`), its own fit set and labels."""
    import argparse

    from learn import cc_build as CB

    a = argparse.Namespace(out=None if not smoke else str(root), smoke=smoke)
    return CB.arm_rows(a, CB.load_plan(a))


ARMS = {
    "D_F5bk": {"runs": _bk_runs, "fit_rows": _bk_fit_rows, "constant_is_d_f5s": True, "model_arm": T.MODEL_ARM,
               "input": "the stored crop's stock X-LANCE stem (D_stem's input, as D_F5); trained on F5 remixed under "
                        "step 1's per-example backings"},
    "D_CC": {"runs": _cc_runs, "fit_rows": _cc_fit_rows, "constant_is_d_f5s": False, "model_arm": T.MODEL_ARM,
             "input": "the stored crop's stock X-LANCE stem (D_stem's input, as D_F5); trained on the clean/crunch "
                      "pool (cc_build), its own fit set FS_CC and constant"},
}
PENDING = {}


def spec_of(arm):
    if arm in PENDING:
        raise SystemExit(f"--arm {arm}: {PENDING[arm]}")
    if arm not in ARMS:
        raise SystemExit(f"--arm in {sorted(ARMS)}")
    return ARMS[arm]


def time_arm(arm):
    return f"{arm}:at-S:{TIME_FAMILY}"


def answer_arms(arm):
    return (arm, time_arm(arm))


def contrasts(arm):
    """{name: (a, b)}: the primary and the co-primary, then the descriptive rows (F5's stored answers on the right)."""
    return {f"{arm} - {T3.FULL} (primary)": (arm, T3.FULL),
            f"{time_arm(arm)} - {time_arm(T3.FULL)} (co-primary: time effects and spring at S)":
                (time_arm(arm), time_arm(T3.FULL)),
            f"{arm} - {T3.CORE} (descriptive)": (arm, T3.CORE),
            f"{arm} - S (descriptive)": (arm, "S"),
            f"{arm} - constant (D_F5's, rendered in F5; descriptive)": (arm, T3.CONST)}


def renders_needed(groups):
    return RENDERS_PER_GROUP * groups


def same_constant(med_json, const_json, f5_model):
    """Whether an arm's constant equals D_F5's stored one (the same labels), NaN equal to NaN."""
    def canon(x):
        return json.dumps(x, sort_keys=True, default=str)
    return canon(med_json) == canon(f5_model["constant"]) and canon(const_json) == canon(f5_model["constant_answers"])


def pedal_arm(arm):
    return f"{arm}:at-S:{PEDALS}"


def const_arm(arm):
    return f"{arm}:constant"


def seed_arms(arm):
    return tuple(f"{arm}:s{s}" for s in T3.TRAIN_SEEDS)


def followup_answers(arm):
    """The follow-ups' rendered answers (amendment 4 (b))."""
    return (pedal_arm(arm), const_arm(arm))


def followup_renders_needed(groups):
    return FOLLOWUP_RENDERS_PER_GROUP * groups


def followup_contrasts(arm):
    """{name: (a, b)} of amendment 4 (b), all descriptive: the arm's own renders are step 3's, F5's are F5's."""
    return {f"{pedal_arm(arm)} - {arm} (descriptive)": (pedal_arm(arm), arm),
            f"{pedal_arm(arm)} - {pedal_arm(T3.FULL)} (descriptive)": (pedal_arm(arm), pedal_arm(T3.FULL)),
            f"{arm} - {const_arm(arm)} (descriptive)": (arm, const_arm(arm)),
            f"{const_arm(arm)} - {T3.CONST} (D_F5's; descriptive)": (const_arm(arm), T3.CONST)}


def drive_summary(answers, cls_of):
    """Amendment 4 (a), descriptive: per answer set and selection (`SELECTIONS`) the directions, how many have each
    drive pedal on, and inputGain's median. answers: {name: {"slug|amp|search": {"settings": {"module/key": stored}}}};
    cls_of: {slug: class}."""
    from statistics import median

    out = {}
    for name, preds in answers.items():
        rows = {}
        for sel, keep in SELECTIONS.items():
            ss = [v["settings"] for k, v in sorted(preds.items()) if keep(k.split("|")[1], cls_of[k.split("|")[0]])]
            gains = [float(s[INPUT_GAIN]) for s in ss if s.get(INPUT_GAIN) not in (None, "")]
            rows[sel] = {"directions": len(ss), **{d: sum(s.get(d) == "true" for s in ss) for d in DRIVES},
                         "input_gain_median": median(gains) if gains else None}
        out[name] = rows
    return out


def runaway_prone(preds):
    """How many answers have the delay on with feedback >= RUNAWAY_FEEDBACK (the runaway scan's pattern)."""
    return sum(1 for v in preds.values() if v["settings"].get("delay/delayActive") == "true"
               and float(v["settings"].get("delay/delayFeedback") or 0.0) >= RUNAWAY_FEEDBACK)


# --- I/O -------------------------------------------------------------------------------------------------------------

def out_dir(root, arm):
    return pathlib.Path(root) / OUT_DIR / arm


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def ledger_declared():
    d = json.loads((V.PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text())
    e = next((t for t in d["tests"] if t["test_id"] == T3.LEDGER_ID), {})
    return LEDGER_MARK in str(e.get(LEDGER_KEY, ""))


def require_readout(args):
    T3.require_t3(args)
    if not args.smoke and not ledger_declared():
        raise SystemExit(f"the ledger's {T3.LEDGER_ID} has no {LEDGER_KEY} declaring '{LEDGER_MARK}': real runs refuse")
    return spec_of(args.arm)


def followup_declared():
    d = json.loads((V.PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text())
    e = next((t for t in d["tests"] if t["test_id"] == FOLLOWUP_LEDGER_ID), {})
    return FOLLOWUP_MARK in str(e.get(FOLLOWUP_KEY, ""))


def require_followup(args):
    spec = require_readout(args)
    if args.arm not in FOLLOWUP_ARMS:
        raise SystemExit(f"the follow-ups are declared for {FOLLOWUP_ARMS} only")
    if not args.smoke and not followup_declared():
        raise SystemExit(f"the ledger's {FOLLOWUP_LEDGER_ID} has no {FOLLOWUP_KEY} declaring '{FOLLOWUP_MARK}': "
                         "real runs refuse")
    return spec


def followup_dir(root, arm):
    return out_dir(root, arm) / FOLLOWUP_DIR


def load_models(root, arm, spec, smoke=False):
    import torch

    nets, recs = [], []
    for s in T3.TRAIN_SEEDS:
        p = spec["runs"](root, s)
        rec = _load(p)
        if not rec or (rec.get("smoke") and not smoke):
            raise SystemExit(f"{arm} seed {s} has no run")
        net = F.build_net()
        net.load_state_dict(torch.load(p.with_suffix(".pt"), map_location="cpu"))
        net.eval()
        nets.append(net)
        recs.append(rec)
    return nets, recs


def model_shas(recs):
    return {str(r["seed"]): r["model_sha256"] for r in recs}


def load_fit(root, arm, smoke=False):
    fit = _load(out_dir(root, arm) / "fit.json")
    if not fit or (fit.get("smoke") and not smoke):
        raise SystemExit(f"run `fit --arm {arm}` first")
    return fit


# --- fit (TORCH_PY; zero renders) ------------------------------------------------------------------------------------

def cmd_fit(args):
    """The arm's constant (D_F5bk: refused unless it equals D_F5's stored one) and amendment 5's pull on its fit set,
    with b refitted on the fit set's two section folds (printed); the amp head's accuracy there."""
    import numpy as np

    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import trusted_data_t3_mix as TM
    from learn import trusted_data_t3_r as R

    spec = require_readout(args)
    root = V.out_root(args)
    plan, drift = TM.load_frozen(root, args.smoke)
    ctx = DS.Ctx(quiet=True)
    tr_rows, fs_rows, files = spec["fit_rows"](root, ctx, plan, smoke=args.smoke)
    enc = T3.encode_for(T3.FULL)
    enc6 = (lambda lab: enc(lab)[:6])
    med = DS.label_medians(tr_rows, enc6)
    const = G.constant_answers(tr_rows, enc6, len(F.CONT), len(F.SW), len(F.CAT))
    if spec["constant_is_d_f5s"]:
        f5fit = R.load_fit(root)
        if [r["i"] for r in fs_rows] != f5fit["fs5_ids"]:
            raise SystemExit("the fit set differs from the FS5 F5's fit.json read")
        if not same_constant(DS.medians_json(med), G.const_json(const), f5fit["models"][T3.FULL]) and not args.smoke:
            raise SystemExit(f"{args.arm}'s constant differs from D_F5's stored one: the labels are not D_F5's")
    cell_of = {r["i"]: (r["amp"], r["base"]) for r in fs_rows}
    folds = DS.section_folds(fs_rows)
    amp_of = {r["i"]: r["amp"] for r in fs_rows}
    nets, recs = load_models(root, args.arm, spec, args.smoke)
    X, C, Y, who = T3.fs_tensors(fs_rows, files, enc6, model_arm=spec["model_arm"])
    outs = F.run_nets(nets, X, C)
    _, ans = DS.median_answers(outs, who)
    lab = DS.labels_of(who, Y)
    table = DS.fit_pull_table(ans, lab, cell_of, med)
    fold_tables = {f: DS.fit_pull_table({i: a for i, a in ans.items() if folds[i] == f}, lab, cell_of, med)
                   for f in (0, 1)}
    amp_acc = [float(int(np.argmax(np.mean([F._softmax(o[n][5]) for o in outs], axis=0))) == F.AMPS.index(amp_of[i]))
               for n, i in enumerate(who)]
    ent = {"models": model_shas(recs), "input": spec["input"], "constant": DS.medians_json(med),
           "constant_answers": G.const_json(const), "constant_is_d_f5s": spec["constant_is_d_f5s"],
           "pull": DS.table_json(table), "pull_summary": DS.pull_summary(table),
           "pull_folds": {str(f): DS.pull_summary(t) for f, t in fold_tables.items()},
           "fit_examples": len(fs_rows), "fit_sections": len({r["section"] for r in fs_rows}),
           "fit_ids": [r["i"] for r in fs_rows],
           "amp_head_fit_accuracy": float(np.mean(amp_acc)) if amp_acc else None}
    print(f"{args.arm}: pull {ent['pull_summary']}; folds {ent['pull_folds']}; amp head accuracy "
          f"{ent['amp_head_fit_accuracy']}", flush=True)
    _save(out_dir(root, args.arm) / "fit.json", {
        "plan": PLAN, "stage": f"{args.arm} fit", "ledger": f"{T3.LEDGER_ID} {LEDGER_KEY}",
        "readout_rule": DS.READOUT_RULE + " (T3's)", "model": ent, "drift": drift, "smoke": bool(args.smoke),
        "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"FIT DONE {args.arm}")


# --- vreal-predict (TORCH_PY; zero renders) ----------------------------------------------------------------------------

def cmd_vreal_predict(args):
    """The arm's answers on the frozen V-real-11 (zero renders): the crop's inputs through F5's step-4 path (input
    hashes equal to F5's), pulled by the arm's own fit; the same answer with the time-effect and spring heads at S;
    the arm's own amp recorded. Output gain stays S's here and is fitted at render."""
    from learn import arm_a_mega53 as A
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import local_objective as LO
    from learn import trusted_data_t3_mix as TM

    spec = require_readout(args)
    root = V.out_root(args)
    plan, drift = TM.load_frozen(root, args.smoke)
    fit = load_fit(root, args.arm, args.smoke)
    nets, recs = load_models(root, args.arm, spec, args.smoke)
    if fit["model"]["models"] != model_shas(recs):
        raise SystemExit(f"{args.arm}: the fit was made with other models")
    med, table = DS.medians_from_json(fit["model"]["constant"]), DS.table_from_json(fit["model"]["pull"])
    f5pred, f5pp = TM.f5_predictions(root, plan, args.smoke)
    dirs, parts, dropped = T3.vreal_dirs(root, plan, bool(f5pred.get("dropped_members")))
    if sorted(dropped) != sorted(f5pred.get("dropped_members") or []):
        raise SystemExit("V-real's parts changed since F5's predictions")
    man = DS._load(DS.stems_manifest_path(DS.ROOT, T.SEP))
    target = json.loads(DE.LEVELS.read_text())["summary"]["eval_mix_lufs_median"]
    ms = A.L.menu_S()
    preds = {a: {} for a in answer_arms(args.arm)}
    own, inputs, gaps = {}, {}, {}
    for slug, amp, search, held in dirs:
        cls, _ = T3.part_info(slug, parts[slug])
        if slug not in inputs:
            inputs[slug] = TM.vreal_input(slug, parts[slug], man, target)
            if inputs[slug]["hashes"] != f5pred["inputs"].get(slug) and not args.smoke:
                raise SystemExit(f"{slug}: its inputs differ from those F5's predictions read")
        it = inputs[slug]
        s8, m8, ls, lm = DS.step4_half(it["stem"], it["mix"], search, it["gain_db"])
        _, S = ms[amp][cls]
        key = f"{slug}|{amp}|{search}"
        x, c = DS.model_input(s8, m8, ls, lm, search, amp, cls, spec["model_arm"])
        b, gap = DS.cell_b(table, (amp, cls), F.cell_masks(amp)[0])
        if gap:
            gaps[f"{amp}|{cls}"] = gap
        r = F.readout([o[0] for o in F.run_nets(nets, [x], [c])])
        diag = {"a2": [float(v) for v in r["a2"]], "sw_p": [float(v) for v in r["sw_p"]], "mics": r["mics"]}
        for a, at_S in ((args.arm, ()), (time_arm(args.arm), (TIME_FAMILY,))):
            preds[a][key] = {"settings": LO.sdict(T3.full_answer(amp, S, r, med[(amp, cls)], b, at_S=at_S)),
                             "held": held, "diag": diag}
        own[f"{slug}|{search}"] = {"amp": r["amp"], "p": r["amp_p"]}
    od = out_dir(root, args.arm) / "vreal"
    refuse_stale_groups(_load(od / "predictions.json"), model_shas(recs), sha(out_dir(root, args.arm) / "fit.json"),
                        od / "groups")
    _save(od / "predictions.json", {
        "plan": PLAN, "stage": f"{args.arm} V-real", "ledger": f"{T3.LEDGER_ID} {LEDGER_KEY}",
        "arms": list(answer_arms(args.arm)), "input": spec["input"], "smoke": bool(args.smoke),
        "members": plan["vreal"]["members"], "dropped_members": dropped, "directions": len(dirs),
        "predictions": preds, "own_amp": own, "pull_gaps": gaps, "inputs": {s: v["hashes"] for s, v in inputs.items()},
        "models": model_shas(recs), "fit_sha256": sha(out_dir(root, args.arm) / "fit.json"),
        "f5_predictions_sha256": sha(f5pp), "drift": drift,
        "output_gain": "S's here; fitted per answer at render to the stem's loudness, as F5 (" + F.OUTPUT_FIT_STATUS + ")",
        "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    groups = len({(s, a) for s, a, _, _ in dirs})
    print(f"PREDICT DONE {args.arm}: {len(dirs)} directions x {ANSWERS_PER_ARM} answers; {groups} groups, "
          f"{renders_needed(groups)} renders to come" + (f"; dims with no fitted pull {gaps}" if gaps else ""))


def refuse_stale_groups(prev, models, fit_sha, groups_dir):
    """T3's guard: new predictions may not replace ones V-real was already rendered from (other models or another
    fit), or a resumed render would mix two model sets' answers in one report."""
    if prev and (prev.get("models") != models or prev.get("fit_sha256") != fit_sha) and \
            any(pathlib.Path(groups_dir).glob("*.json")):
        raise SystemExit(f"V-real was rendered from other models' predictions: move {pathlib.Path(groups_dir).parent} aside first")


def cmd_followup_predict(args):
    """Amendment 4's answers on the frozen V-real-11 (zero renders), the inputs exactly as step 3's (hashes equal to
    those its predictions recorded): step 3's two answers recomputed (they must equal the stored ones); (a) each
    seed's own answer and amp head; (b) the arm with the pedal family at S and the arm's own constant. Output gain
    stays S's here and is fitted at render."""
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import direct_existing as DE
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import local_objective as LO
    from learn import trusted_data_t3_mix as TM

    spec = require_followup(args)
    root = V.out_root(args)
    plan, drift = TM.load_frozen(root, args.smoke)
    fit = load_fit(root, args.arm, args.smoke)
    fit_sha = sha(out_dir(root, args.arm) / "fit.json")
    nets, recs = load_models(root, args.arm, spec, args.smoke)
    if fit["model"]["models"] != model_shas(recs):
        raise SystemExit(f"{args.arm}: the fit was made with other models")
    bp = out_dir(root, args.arm) / "vreal" / "predictions.json"
    base = _load(bp)
    if not base or (base.get("smoke") and not args.smoke):
        raise SystemExit(f"step 3's predictions for {args.arm} are missing")
    if base["models"] != model_shas(recs) or base["fit_sha256"] != fit_sha:
        raise SystemExit("step 3's predictions were made with other models or another fit")
    med, table = DS.medians_from_json(fit["model"]["constant"]), DS.table_from_json(fit["model"]["pull"])
    const = G.const_from_json(fit["model"]["constant_answers"])
    f5pred, f5pp = TM.f5_predictions(root, plan, args.smoke)
    dirs, parts, dropped = T3.vreal_dirs(root, plan, bool(base.get("dropped_members")))
    if sorted(dropped) != sorted(base.get("dropped_members") or []):
        raise SystemExit("V-real's parts changed since step 3's predictions")
    man = DS._load(DS.stems_manifest_path(DS.ROOT, T.SEP))
    target = json.loads(DE.LEVELS.read_text())["summary"]["eval_mix_lufs_median"]
    ms = A.L.menu_S()
    rendered, seeds = followup_answers(args.arm), seed_arms(args.arm)
    preds = {a: {} for a in rendered + seeds}
    own_seed, inputs, classes, differ = {}, {}, {}, []
    for slug, amp, search, held in dirs:
        cls, _ = T3.part_info(slug, parts[slug])
        classes[slug] = cls
        if slug not in inputs:
            inputs[slug] = TM.vreal_input(slug, parts[slug], man, target)
            if inputs[slug]["hashes"] != base["inputs"].get(slug) and not args.smoke:
                raise SystemExit(f"{slug}: its inputs differ from those step 3's predictions read")
        it = inputs[slug]
        s8, m8, ls, lm = DS.step4_half(it["stem"], it["mix"], search, it["gain_db"])
        _, S = ms[amp][cls]
        key = f"{slug}|{amp}|{search}"
        x, c = DS.model_input(s8, m8, ls, lm, search, amp, cls, spec["model_arm"])
        b, _ = DS.cell_b(table, (amp, cls), F.cell_masks(amp)[0])
        m = med[(amp, cls)]
        outs = F.run_nets(nets, [x], [c])
        r = F.readout([o[0] for o in outs])
        for a, at_S in ((args.arm, ()), (time_arm(args.arm), (TIME_FAMILY,))):
            if LO.sdict(T3.full_answer(amp, S, r, m, b, at_S=at_S)) != base["predictions"][a][key]["settings"]:
                differ.append(f"{a}|{key}")
        preds[pedal_arm(args.arm)][key] = {"settings": LO.sdict(T3.full_answer(amp, S, r, m, b, at_S=(PEDALS,))),
                                           "held": held}
        preds[const_arm(args.arm)][key] = {"settings": LO.sdict(T3.constant_full(amp, S, const[(amp, cls)])),
                                           "held": held}
        for k, a in enumerate(seeds):
            preds[a][key] = {"settings": LO.sdict(T3.full_answer(amp, S, r, m, b, seed=k)), "held": held,
                             "sw_p": [float(v) for v in r["sw_p_seed"][k]]}
        own_seed[f"{slug}|{search}"] = [None if o[0][5] is None else
                                        {"amp": F.AMPS[int(np.argmax(F._softmax(o[0][5])))],
                                         "p": [float(v) for v in F._softmax(o[0][5])]} for o in outs]
    if differ and not args.smoke:
        raise SystemExit(f"{len(differ)} of step 3's answers do not recompute to the stored ones (e.g. {differ[:3]}): "
                         "nothing written")
    f5 = f5pred["predictions"]
    drives = drive_summary({args.arm: base["predictions"][args.arm], **{a: preds[a] for a in seeds},
                            const_arm(args.arm): preds[const_arm(args.arm)], T3.FULL: f5[T3.FULL],
                            **{f"{T3.FULL}:s{s}": f5[f"{T3.FULL}:s{s}"] for s in T3.TRAIN_SEEDS},
                            T3.CONST: f5[T3.CONST]}, classes)
    od = followup_dir(root, args.arm)
    refuse_stale_groups(_load(od / "predictions.json"), model_shas(recs), fit_sha, od / "groups")
    _save(od / "predictions.json", {
        "plan": PLAN, "stage": f"{args.arm} follow-ups", "ledger": f"{FOLLOWUP_LEDGER_ID} {FOLLOWUP_KEY}",
        "arms": list(rendered), "seed_arms": list(seeds), "input": spec["input"], "smoke": bool(args.smoke),
        "members": plan["vreal"]["members"], "dropped_members": dropped, "directions": len(dirs),
        "predictions": preds, "own_amp_seed": own_seed, "classes": classes, "drives": drives,
        "runaway_prone": {a: runaway_prone(v) for a, v in preds.items()},
        "recomputed_step3_answers_equal": not differ, "inputs": {s: v["hashes"] for s, v in inputs.items()},
        "models": model_shas(recs), "fit_sha256": fit_sha, "step3_predictions_sha256": sha(bp),
        "f5_predictions_sha256": sha(f5pp), "drift": drift,
        "output_gain": "S's here; fitted per answer at render to the stem's loudness, as F5 (" + F.OUTPUT_FIT_STATUS + ")",
        "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print_drives(drives)
    print(f"  delay on with feedback >= {RUNAWAY_FEEDBACK}: " +
          ", ".join(f"{a} {runaway_prone(v)}/{len(v)}" for a, v in preds.items()), flush=True)
    pooled = {k: (v or {}).get("amp") for k, v in (base.get("own_amp") or {}).items()}
    for n, a in enumerate(seeds):
        same = sum(1 for k, v in own_seed.items() if v[n] and v[n]["amp"] == pooled.get(k))
        print(f"  {a}: its amp head agrees with the pooled one on {same} of {len(own_seed)} (part, half)s", flush=True)
    groups = len({(s, a) for s, a, _, _ in dirs})
    print(f"FOLLOWUP PREDICT DONE {args.arm}: {len(dirs)} directions; step 3's answers recomputed equal; "
          f"{groups} groups, {followup_renders_needed(groups)} renders to come")


def print_drives(drives):
    for name, rows in drives.items():
        print(f"  {name:28s} " + "; ".join(
            f"{sel}: drive1 {r[DRIVES[0]]}/{r['directions']}, drive2 {r[DRIVES[1]]}/{r['directions']}, inputGain "
            f"{r['input_gain_median']}" for sel, r in rows.items()), flush=True)


# --- vreal-render (MAIN; renders) --------------------------------------------------------------------------------------

def cmd_vreal_render(args):
    """The arm's V-real renders for one shard of (part, amp) groups: one discarded priming render at S, then each
    answer once per direction, judged on both halves; output gain fitted to the stem's loudness and its |LUFS error|
    recorded (as F5). isolate=True; at most 3 render processes machine-wide; the 31 GB disk guard; a done group is
    kept."""
    require_readout(args)
    root = V.out_root(args)
    render_answers(args, root, out_dir(root, args.arm) / "vreal", f"run `vreal-predict --arm {args.arm}` first")


def cmd_followup_render(args):
    """Amendment 4 (b)'s renders, step 3's recipe (`render_answers`) on the follow-ups' two answers."""
    require_followup(args)
    root = V.out_root(args)
    render_answers(args, root, followup_dir(root, args.arm), f"run `followup-predict --arm {args.arm}` first")


def render_answers(args, root, od, missing):
    """One shard of (part, amp) groups for the answers `od/predictions.json` names in "arms", to `od/groups/`."""
    from learn import arm_a_mega53 as A
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import trusted_data_t3_mix as TM

    plan, _ = TM.load_frozen(root, args.smoke)
    pred = _load(od / "predictions.json")
    if not pred or (pred.get("smoke") and not args.smoke):
        raise SystemExit(missing)
    if pred["members"] != plan["vreal"]["members"]:
        raise SystemExit("the predictions were made for another V-real membership")
    if pred["fit_sha256"] != sha(out_dir(root, args.arm) / "fit.json"):
        raise SystemExit("fit.json changed since vreal-predict")
    dirs, parts, dropped = T3.vreal_dirs(root, plan, bool(pred.get("dropped_members")))
    if sorted(dropped) != sorted(pred.get("dropped_members") or []):
        raise SystemExit("V-real's parts changed since vreal-predict")
    if PS.free_gb() < T.DISK_GUARD_GB:
        raise SystemExit(f"free disk below {T.DISK_GUARD_GB:.0f} GB")
    arms = tuple(pred["arms"])
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
                            for sh, _ in K.DIRECTIONS} for a in arms}
            held_of = dict(K.DIRECTIONS)
            checks = {}

            def keep(arm, search, y, settings=settings, stem=stem, ref=g["ref"], checks=checks):
                gain = float(settings[arm][search].get(F.OUTPUT, "0"))
                checks[f"{arm}|{search}"] = T3.lufs_check(gain, y, stem, ref, search, held_of[search])

            rec = DS.run_group(rr, g, settings, False, None, K.judge, keep=keep, arms=arms)
            rec.update(slug=slug, amp=amp, lufs=checks, output_gain_fit=F.OUTPUT_FIT_STATUS)
            _save(gp, rec)
            print(slug, amp, rec["renders"], flush=True)
    finally:
        rr.close()
    print(f"RENDER DONE {args.arm} {args.shard[0]}/{args.shard[1]}; renders {rr.count}")


# --- report (MAIN; zero renders) ---------------------------------------------------------------------------------------

def cmd_report(args):
    """The rows (`contrasts`): band-weighted, 90% band-clustered t (7 bands), per class and V-real-10 beside; F5's
    stored renders for D_F5, its time-effects family answer, D_core5, S and the constant."""
    require_readout(args)
    root = V.out_root(args)
    od = out_dir(root, args.arm) / "vreal"
    read_rows(args, root, {a: od for a in answer_arms(args.arm)}, contrasts(args.arm), od,
              out_dir(root, args.arm) / "report.json", f"{args.arm} report", f"{T3.LEDGER_ID} {LEDGER_KEY}",
              {"own_amp": (_load(od / "predictions.json") or {}).get("own_amp")})
    print(f"REPORT DONE {args.arm}")


def cmd_followup_report(args):
    """Amendment 4: (a)'s drive table again, and (b)'s rows (`followup_contrasts`), as step 3's report reads them;
    the arm's own renders from step 3, the new answers from the follow-ups, the rest from F5."""
    require_followup(args)
    root = V.out_root(args)
    od, fd = out_dir(root, args.arm) / "vreal", followup_dir(root, args.arm)
    fp = _load(fd / "predictions.json")
    if not fp or (fp.get("smoke") and not args.smoke):
        raise SystemExit(f"run `followup-predict --arm {args.arm}` first")
    print_drives(fp["drives"])
    read_rows(args, root, {args.arm: od, **{a: fd for a in followup_answers(args.arm)}}, followup_contrasts(args.arm),
              fd, fd / "report.json", f"{args.arm} follow-ups report", f"{FOLLOWUP_LEDGER_ID} {FOLLOWUP_KEY}",
              {"drives": fp["drives"], "own_amp_seed": fp.get("own_amp_seed")})
    print(f"FOLLOWUP REPORT DONE {args.arm}")


def read_rows(args, root, where, con_pairs, rdir, out_path, stage, ledger, extra):
    """The rows `con_pairs` names: each answer's renders from `where` (else F5's stored ones), band-weighted with 90%
    band-clustered t (7 bands), per class, part-weighted and V-real-10 beside; renders and |LUFS error| from `rdir`."""
    from learn import arm_a_mega53 as A
    from learn import direct_stems as DS
    from learn import perfect_sep_arm as P
    from learn import trusted_data_t3_mix as TM

    plan, drift = TM.load_frozen(root, args.smoke)
    f5d = T.stage_root(root, T3.STAGE) / "vreal"
    pred, _ = TM.f5_predictions(root, plan, args.smoke)
    members = set(plan["vreal"]["members"]) - set(pred.get("dropped_members") or [])
    v10 = set(plan["vreal"]["v_real_10"])
    crops = (_load(T3.crops_manifest_path(root)) or {}).get("crops") or {}
    parts, _ = T3.vreal_parts(sorted(members), A.pool_slugs(), crops, drop_missing=True)
    units = [u for u in P.build_units() if u["slug"] in members] + T3.t3_units(parts, f5d / "groups")
    cache = {}

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

    arms = sorted({a for pair in con_pairs.values() for a in pair} - {"S"})
    refused = {a: DS.add_step4_arm(units, a, value(a)) for a in arms}
    gaps = [f"{n} directions have no {a} value" for a in arms if (n := sum(1 for u in units if u["d"].get(a) is None))]
    bad = {a: n for a, n in refused.items() if n}
    if bad:
        gaps.append(f"refused answers scored as S {bad}")
    rows_ = ("all", "v_real_10")
    filt = {"all": lambda u: True, "v_real_10": lambda u: u["slug"] in v10}
    con = {name: DS.step4_contrast(units, a, b, filt, rows=rows_, fixed=("S",)) for name, (a, b) in con_pairs.items()}
    lufs = []
    for (d, *_), gr in cache.items():
        if d == str(rdir):
            lufs += list((gr.get("lufs") or {}).values())
    renders = sum((_load(p) or {}).get("renders", 0) for p in (rdir / "groups").glob("*.json"))
    rep = {"plan": PLAN, "stage": stage, "ledger": ledger,
           "v_real": sorted(members), "directions": len(units), "complete": not gaps, "incomplete_because": gaps,
           "refused_scored_as_S": refused, "contrasts": con, "abs_lufs_error": T3.lufs_summary(lufs),
           **extra, "renders": renders, "drift": drift,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(out_path, rep)
    print(f"{args.arm}: V-real {len(members)} parts ({len(units)} directions); renders {renders}")
    for g in gaps:
        print(f"  incomplete: {g}")
    for name, c in con.items():
        for row in rows_:
            r = c["rows"].get(row) or {}
            for cls, s in [("", r.get("all") or {})] + sorted((r.get("per_class") or {}).items()):
                sign = (f"; bands -/=/+ {s.get('bands_negative')}/"
                        f"{s['bands'] - (s.get('bands_negative') or 0) - (s.get('bands_positive') or 0)}/"
                        f"{s.get('bands_positive')}") if s.get("bands") else ""
                print(f"  {name if not cls and row == 'all' else '':70s} {(row + ' ' + cls).strip():18s} "
                      f"{s.get('band_weighted_mean')} [{s.get('lo90')}, {s.get('hi90')}] ({s.get('bands')} bands{sign}) "
                      f"{T3.rule_reading(s)}")
            pw = r.get("part_weighted")
            if pw:
                print(f"  {'':70s} {(row + ' part-weighted'):18s} {pw}")
    print(f"|LUFS error| (a pipeline check): {rep['abs_lufs_error']}")


# --- main ------------------------------------------------------------------------------------------------------------

COMMANDS = {"fit": cmd_fit, "vreal-predict": cmd_vreal_predict, "vreal-render": cmd_vreal_render, "report": cmd_report,
            "followup-predict": cmd_followup_predict, "followup-render": cmd_followup_render,
            "followup-report": cmd_followup_report}
RENDER_COMMANDS = ("vreal-render", "followup-render")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cc_readout", description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=tuple(COMMANDS))
    ap.add_argument("--arm", required=True)
    ap.add_argument("--shard", type=V.parse_shard, default=(0, 1))
    ap.add_argument("--out", default=None)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args(argv)
    if args.shard != (0, 1) and args.cmd not in RENDER_COMMANDS:
        raise SystemExit(f"--shard is for {' and '.join(RENDER_COMMANDS)}")
    spec_of(args.arm)
    return COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
