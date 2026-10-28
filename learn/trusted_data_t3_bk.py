"""The clean/crunch pool's backing-only arm, D_F5bk (`docs/clean-crunch-pool-plan.md`, step 3; ledger `trusted-data-t3`,
amendment 6): F5's stored renders remixed under step 1's per-example leak rule and separated again, so D_F5bk differs
from D_F5 in the backing alone. Outputs go to `trusted-data/t3-bk/` only; `t0/`, `t2/` and `t3/` are read, never
written.

    MAIN=/Users/yoavbz/projects/neuraldsp-preset-generator/.venv/bin/python
    MSST=~/ndsp-presets/tools/msst-venv/bin/python; TORCH_PY=~/ndsp-presets/tools/demucs-venv/bin/python
    $MAIN -m learn.trusted_data_t3_bk plan [--dry]                   # zero renders: each example's new backing
    $MSST -m learn.trusted_data_t3_bk control --device mps|cpu       # the pipeline control (old backing reproduces T3)
    $MSST -m learn.trusted_data_t3_bk build --device mps|cpu         # remix and X-LANCE, on T3's build device
    $MAIN -m learn.trusted_data_t3_bk check                          # every changed example built, nothing refused
    $TORCH_PY -m learn.trusted_data_t3_bk train --seed 20261042|20261043   # D_F5's recipe on the new inputs

**What changes.** Each F5 and FS5 example (T3's frozen plan under step (a)'s drift check) keeps T2's other-guitar
renders, pans and mix draw, T3's full-twin target render and its labels; only the stems summed into the backing are
the per-example rule's (`trusted_data.stems_for` with `stem_takes` on the guitars the example replaces,
`replaced_sources` with the inventory's own amp tracks), the vocal variant chosen as T2 chose it
(`vocals_drawn` and the variants differ). An example with a target-double amp-track stand-in
(`trusted_data.target_doubles`) is left out, as the clean/crunch pool leaves it out; T2 has none. An example whose
stems do not change keeps T3's stored mix and stem features (the same inputs on the same device). A changed example
is rebuilt by `trusted_data.self_built_mix` and separated on the device T3 built it on, so the separator's device
noise matches D_F5's. `self_built_mix` holds the drawn guitar-to-backing ratio, so a louder backing gets a lower gain
(first builds' median -4.8 dB Death Of A Romantic, -2.3 dB Storm Of Particles): the other guitars sit that much lower
against the target and the stem's SNR rises (median +4.5 / +1.0 dB). Read D_F5bk - D_F5 with this beside it.

**Resuming and re-planning.** Build and control rows record their backing's track hash (`tracks_sha`) and count as
done only on the plan's backing; rows from before that (the first builds) count only while `t3-bk/plan.json` is the
file they ran on (`LEGACY_PLAN_SHA`), and `plan` refuses to rewrite the plan while such rows exist.

**The pipeline control.** Before any build: per section with a changed example, its first changed example rebuilt
with T2's old stems on its stored device must reproduce T3's stored `mix-t3` and `xlance_g-t3` (match share 0.99 on
both halves); `build` refuses until every control passed.

**Training.** D_F5's recipe exactly (`trusted_data_t3.cmd_train` for D_F5: 115-control heads, the masked loss and the
amp head, D_stem's input augmented with the full twins' target mels as merge partners, early stopping on FS5, seeds
20261042 and 20261043); it refuses unless every changed example is built, none refused, and its examples are D_F5's.
The readout (V-real-11, D_F5bk - D_F5, time-effect heads at S co-primary) is the plan's, declared in amendment 6;
its commands come with the step-3 readout code. Not before the user's ear clears the leak rule (the part-11 page's
5 backing cards).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import time

from learn import trusted_data as T
from learn import trusted_data_t3 as T3
from learn import verify_tracks as V

OUT_DIR = "t3-bk"                                    # trusted-data/t3-bk/: never under t3/
ARM = "D_F5bk"
STAGE = "bk"                                         # feature kinds mix-bk and xlance_g-bk
LEDGER_KEY = "amendment_6"
LEDGER_MARK = "D_F5bk (clean/crunch pool step 3)"
PLAN = "docs/clean-crunch-pool-plan.md"
DEVICES = ("mps", "cpu")
# The plan file the first builds ran on (2026-10-28 22:43): their rows predate the backing hash, so they count as
# done only while t3-bk/plan.json is still exactly this file (PR #325's review).
LEGACY_PLAN_SHA = "a2f398fdc7022a07c421106d39366c7f6b35af4e2fa47f12b556e2333439c06d"

_save, _load = V._save, V._load


# --- pure ------------------------------------------------------------------------------------------------------------

def vocal_variant(x, v, n):
    """T2's vocal choice on a variant pair: vocals when drawn and the variants differ."""
    return bool(x["draw"]["vocals_drawn"] and v != n)


def backing_of(x, v, n):
    """The tracks summed into the example's backing (`trusted_data.backing_tracks` on the new stems)."""
    return T.backing_tracks({**x, "stems": {"v": v, "n": n}}, vocal_variant(x, v, n))


def example_entry(x, v, n, doubles, set_name, device):
    """One example's record in the plan: old and new stems and backings (the tracks summed, as built), whether the
    backing changes, why it is left out."""
    new, old = backing_of(x, v, n), T.backing_tracks(x, vocal_variant(x, x["stems"]["v"], x["stems"]["n"]))
    return {"i": x["i"], "set": set_name, "band": x["band"], "section": x["section"], "device": device,
            "old": {"v": list(x["stems"]["v"]), "n": list(x["stems"]["n"])}, "new": {"v": list(v), "n": list(n)},
            "vocals": vocal_variant(x, v, n), "backing": new, "backing_old": old, "same": new == old,
            "left_out": f"a target-double stand-in: {doubles}" if doubles else None}


def tracks_sha(tracks):
    """A short hash of a backing's track list (in order): what a build or control row was made from."""
    return hashlib.sha256(json.dumps(list(tracks)).encode()).hexdigest()[:16] if tracks is not None else None


def entry_backing(e):
    """The tracks a plan entry's new backing sums: the stored list, or for the first plan (written before entries
    stored it) the new variant T2's vocal choice picked (`vocals`); T2 has no amp-track stand-ins."""
    if "backing" in e:
        return e["backing"]
    return list(e["new"]["v" if e["vocals"] else "n"])


def row_current(row, want, plan_sha):
    """Whether a build or control row was made from the backing the plan now asks for (`want`: its tracks_sha). A row
    without a hash (the first builds, before PR #325's review), or a plan entry that cannot name its backing (the first
    plan's old backing, `want` None), counts only while the plan is the file the first builds ran on."""
    if row is None or row.get("refused"):
        return False
    if row.get("backing_sha") is None or want is None:
        return plan_sha == LEGACY_PLAN_SHA
    return row["backing_sha"] == want


def bk_stems(ctx, x, verified_stems, scan, floor):
    """(with vocals, without vocals): example x's stems under the per-example rule, computed as
    `trusted_data.example_recipe(takes=(scan, floor))` computes them (its target and rendered other guitars replaced;
    the inventory's own amp tracks)."""
    rec = ctx.inv[x["di"]]
    sd = rec["session_dir"]
    st = scan.get(sd)
    if not st:
        return [], []
    dis = [x["di"]] + [o["di"] for o in x["others"]]
    rep = T.replaced_sources(st["sources"], dis, {d: ctx.inv[d].get("own") for d in dis})
    return T.stems_for(rec, verified_stems, sd, st, rep, floor)


def train_refusals(p, build_rows, control_rows, stem_exists, plan_sha, tr_ids, es_ids, f5_why):
    """Why D_F5bk may not train yet (empty: it may): a changed example not built from the plan's backing, refused,
    or its stem file missing; an example left out; a pipeline control not passed; the F5/FS5 examples not the plan's;
    the examples not D_F5's (`f5_why`, trusted_data_t3_mix.same_examples)."""
    why = []
    for e in p["examples"]:
        if e["left_out"]:
            why.append((e["i"], f"left out: {e['left_out']}"))
        elif not e["same"]:
            r = build_rows.get(e["i"])
            if r is not None and r.get("refused"):
                why.append((e["i"], f"refused: {r['refused']}"))
            elif not row_current(r, tracks_sha(entry_backing(e)), plan_sha) or not stem_exists(e["i"]):
                why.append((e["i"], "not built from the plan's backing"))
    ent = {e["i"]: e for e in p["examples"]}
    for i in p["control"]:
        r = control_rows.get(i)
        if not (r or {}).get("ok") or not row_current(r, tracks_sha(ent[i].get("backing_old")), plan_sha):
            why.append((i, "pipeline control not passed"))
    if list(tr_ids) != list(p["f5"]) or list(es_ids) != list(p["fs5"]):
        why.append((None, "the F5/FS5 examples differ from this stage's plan"))
    if f5_why:
        why.append((None, f"not D_F5's examples: {f5_why}"))
    return why


def control_ids(entries):
    """The pipeline control's examples: per section with a changed example, its first (by id)."""
    first = {}
    for e in sorted(entries, key=lambda e: e["i"]):
        if not e["same"] and not e["left_out"]:
            first.setdefault(e["section"], e["i"])
    return sorted(first.values())


def build_jobs(entries, device):
    """The changed, kept examples T3 built on this device."""
    return [e["i"] for e in entries if not e["same"] and not e["left_out"] and e["device"] == device]


def files_for(entry, root):
    """(mix, stem) feature files: T3's stored ones for an unchanged example, this stage's for a changed one."""
    if entry["same"]:
        return T3.files_of(root, T3.FULL, entry["i"])
    return str(feat_path(root, entry["i"], "mix")), str(feat_path(root, entry["i"], "stem"))


def summary(entries):
    """Per band: examples, changed, left out, mean stems (no vocals) old and new."""
    out = {}
    for e in entries:
        b = out.setdefault(e["band"], {"examples": 0, "changed": 0, "left_out": 0, "stems_old": 0.0, "stems_new": 0.0})
        b["examples"] += 1
        b["changed"] += int(not e["same"])
        b["left_out"] += int(bool(e["left_out"]))
        b["stems_old"] += len(e["old"]["n"])
        b["stems_new"] += len(e["new"]["n"])
    for b in out.values():
        b["stems_old"] = round(b["stems_old"] / b["examples"], 1)
        b["stems_new"] = round(b["stems_new"] / b["examples"], 1)
    return out


# --- paths, the ledger -----------------------------------------------------------------------------------------------

def out_dir(root):
    return pathlib.Path(root) / OUT_DIR


def plan_file(root):
    return out_dir(root) / "plan.json"


def plan_sha(root):
    f = plan_file(root)
    return hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None


def feat_path(root, i, what):
    from learn import direct_stems as DS

    return DS.ex_path(out_dir(root), i, f"{'mix' if what == 'mix' else T.SEP}-{STAGE}")


def run_path(root, seed):
    return out_dir(root) / "runs" / f"{ARM}-{seed}.json"


def ledger_declared():
    d = json.loads((V.PLUGIN_ROOT / "docs" / "dev-test-ledger.json").read_text())
    e = next((t for t in d["tests"] if t["test_id"] == T3.LEDGER_ID), {})
    return LEDGER_MARK in str(e.get(LEDGER_KEY, ""))


def require_bk(args):
    V.require_real(args)
    if not ledger_declared() and not args.smoke:
        raise SystemExit(f"{ARM} is not declared in the ledger ({T3.LEDGER_ID}, {LEDGER_KEY})")


def rows(root, prefix):
    from learn import direct_stems as DS

    out = {}
    for f in sorted((out_dir(root) / "rows").glob(f"{prefix}-*.jsonl")):
        for r in DS.read_jsonl(f):
            out[r["i"]] = r
    return out


def load_bk_plan(root, smoke=False):
    p = _load(plan_file(root))
    if not p or (p.get("smoke") and not smoke):
        raise SystemExit("run `plan` first")
    return p


# --- commands --------------------------------------------------------------------------------------------------------

def cmd_plan(args):
    """Each F5 and FS5 example's new backing under the per-example rule (zero renders); written to t3-bk/plan.json."""
    from learn import data_cleaning as DC
    from learn import direct_stems as DS
    from learn import trusted_data_t3_mix as TM

    require_bk(args)
    root = V.out_root(args)
    plan, drift = TM.load_frozen(root, args.smoke)
    f5, fs, refused, _ = T3.t3_sets(root, plan)
    tr = T.load_lists(root, args.smoke)
    scan, floor = T.stem_takes(root)
    ctx = DS.Ctx(quiet=True)
    t2 = {x["i"]: x for x in _load(T.plan_path(root, "t2"))["examples"]}
    built = T.rows_of(root, T3.STAGE, "build")
    fss = set(fs)
    entries = []
    for i in f5 + fs:
        x = t2[i]
        rec = ctx.inv[x["di"]]
        sd = rec["session_dir"]
        old = T.stems_for(rec, tr["stems"], sd)
        if (list(old[0]), list(old[1])) != (x["stems"]["v"], x["stems"]["n"]):
            raise SystemExit(f"{i}: the old rule no longer gives T2's stems: the lists moved")
        v, n = bk_stems(ctx, x, tr["stems"], scan, floor)
        doubles = T.target_doubles(rec.get("part") or DC.part_base(x["di"]), x.get("amp_tracks") or [])
        entries.append(example_entry(x, v, n, doubles, "fs5" if i in fss else "f5", built[i].get("device")))
    summ = summary(entries)
    for b, s in sorted(summ.items()):
        print(f"{b:22} {s['examples']:5} examples, {s['changed']:5} changed, {s['left_out']} left out; "
              f"stems {s['stems_old']} -> {s['stems_new']}", flush=True)
    ctl = control_ids(entries)
    jobs = {d: len(build_jobs(entries, d)) for d in DEVICES}
    print(f"pipeline control: {len(ctl)} examples; builds {jobs}", flush=True)
    if args.dry:
        return
    legacy = [r["i"] for r in [*rows(root, "build").values(), *rows(root, "control").values()]
              if r.get("backing_sha") is None]
    if legacy:
        raise SystemExit(f"{len(legacy)} build or control rows predate the backing hash and count only under the "
                         f"current plan file: move t3-bk/rows aside before re-planning")
    _save(plan_file(root), {"plan": PLAN, "stage": f"T3 {ARM}", "ledger": f"{T3.LEDGER_ID} {LEDGER_KEY}",
                            "f5": f5, "fs5": fs, "refused_in_t3": sorted(refused), "floor_db": floor,
                            "drift": drift, "summary": summ, "control": ctl, "jobs": jobs, "examples": entries,
                            "smoke": bool(args.smoke), "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"PLAN DONE {ARM}: {plan_file(root)}")


class _Audio:
    """One example's stored inputs as T3's build read them: T3's full-twin target, T2's other guitars."""

    def __init__(self, root):
        from learn import direct_stems as DS

        self.root = root
        self.t2 = {x["i"]: x for x in _load(T.plan_path(root, "t2"))["examples"]}
        self.t2rend = T.rows_of(root, "t2", "render")
        self.rend = T.rows_of(root, T3.STAGE, "render")
        ctx = DS.Ctx(quiet=True)
        ctx.rows = None
        self.stems = T.Stems(ctx)

    def mix(self, i, tracks):
        """(target, mix, stem-free gains, backing LUFS) of example i with these backing tracks, or None when the
        backing is too quiet for the drawn ratio (T3's refusal)."""
        import numpy as np

        from learn import direct_sound_gate as G

        x = self.t2[i]
        o2 = self.t2rend[i]["others_file"]
        oth = G.read_flac(T.flac_path(self.root, "t2", i, "others"), o2["scale"], o2["sha256"])
        tf = self.rend[i]["target"]
        y = G.read_flac(T.flac_path(self.root, T3.STAGE, i, "target"), tf["scale"], tf["sha256"])
        mix, gains, lb = T.self_built_mix(np.asarray(y, np.float64), np.asarray(oth, np.float64),
                                          self.stems.get(x["section"], tracks), x)
        if not T.empty_backing_ok(y, lb):
            return None
        return np.asarray(y, np.float64), mix, gains, lb


def _separate(sep, mix, i):
    import numpy as np

    s = np.asarray(sep(mix), np.float64)
    if len(s) != len(mix) or not np.isfinite(s).all():
        raise SystemExit(f"{i}: bad stem")
    return s


def cmd_control(args):
    """The pipeline control on this device's control examples: T2's old backing must reproduce T3's stored features."""
    import numpy as np

    from learn import direct_stems as DS

    require_bk(args)
    root = V.out_root(args)
    p = load_bk_plan(root, args.smoke)
    ent = {e["i"]: e for e in p["examples"]}
    psha = plan_sha(root)
    done = rows(root, "control")
    ids = [i for i in p["control"] if ent[i]["device"] == args.device
           and not row_current(done.get(i), tracks_sha(ent[i].get("backing_old")), psha)]
    print(f"control on {args.device}: {len(ids)} to do", flush=True)
    if ids:
        A = _Audio(root)
        sep = DS.stem_separator(T.SEP, args.device)
        rp = out_dir(root) / "rows" / f"control-{args.device}-{os.getpid()}.jsonl"
        rp.parent.mkdir(parents=True, exist_ok=True)
        with open(rp, "a") as fh:
            for i in ids:
                x = A.t2[i]
                old = T.backing_tracks(x, vocal_variant(x, x["stems"]["v"], x["stems"]["n"]))
                if ent[i].get("backing_old") is not None and old != ent[i]["backing_old"]:
                    raise SystemExit(f"{i}: T2's backing differs from the plan's")
                made = A.mix(i, old)
                if made is None:
                    row = {"i": i, "ok": False, "why": "no backing (T3 built this example)",
                           "backing_sha": tracks_sha(old)}
                else:
                    _, mix, _, _ = made
                    s = _separate(sep, mix, i)
                    mm, _, _ = DS.half_features(mix)
                    sm, _, _ = DS.half_features(s)
                    d3m = np.load(T.ex_path(root, T3.STAGE, i, f"mix-{T3.STAGE}"))
                    d3s = np.load(T.ex_path(root, T3.STAGE, i, f"{T.SEP}-{T3.STAGE}"))
                    sh_m = T3.feature_share({"mA": mm["A"], "mB": mm["B"]}, d3m, ("mA", "mB"))
                    sh_s = T3.feature_share({"sA": sm["A"], "sB": sm["B"]}, d3s, ("sA", "sB"))
                    row = {"i": i, "section": x["section"], "device": args.device, "mix_share": sh_m,
                           "stem_share": sh_s, "ok": sh_m >= DS.MATCH_SHARE and sh_s >= DS.MATCH_SHARE,
                           "backing_sha": tracks_sha(old), "plan_sha": psha}
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                print(f"control {i}: {row}", flush=True)
    done = rows(root, "control")
    mine = [done.get(i) or {"i": i} for i in p["control"] if ent[i]["device"] == args.device]
    bad = [r for r in mine if not r.get("ok")
           or not row_current(r, tracks_sha(ent[r["i"]].get("backing_old")), psha)]
    if bad:
        raise SystemExit(f"CONTROL FAILED {args.device}: {bad}")
    print(f"CONTROL DONE {args.device}: {len(mine)} passed")


def control_passed(root, p):
    """The control examples not (yet) passed on the plan's old backing."""
    done, psha = rows(root, "control"), plan_sha(root)
    ent = {e["i"]: e for e in p["examples"]}
    return [i for i in p["control"] if not (done.get(i) or {}).get("ok")
            or not row_current(done[i], tracks_sha(ent[i].get("backing_old")), psha)]


def cmd_build(args):
    """Remix and separate the changed examples T3 built on this device (msst-venv); features saved as `mix-bk` and
    `xlance_g-bk` under t3-bk/, one row per example (the stem file first, then its row)."""
    from learn import direct_stems as DS

    require_bk(args)
    root = V.out_root(args)
    p = load_bk_plan(root, args.smoke)
    missing = control_passed(root, p)
    if missing and not args.smoke:
        raise SystemExit(f"the pipeline control has not passed on {len(missing)} examples: run `control` first")
    ent = {e["i"]: e for e in p["examples"]}
    have, psha = rows(root, "build"), plan_sha(root)
    jobs = [i for i in build_jobs(p["examples"], args.device)
            if not row_current(have.get(i), tracks_sha(entry_backing(ent[i])), psha)
            or not feat_path(root, i, "stem").exists()]
    jobs.sort(key=lambda i: (ent[i]["section"], i), reverse=args.order == "desc")
    jobs = jobs[:args.limit or None]
    print(f"build {ARM} on {args.device}: {len(jobs)} to do", flush=True)
    if not jobs:
        print(f"BUILD DONE {ARM} ({args.device})")
        return
    A = _Audio(root)
    sep = DS.stem_separator(T.SEP, args.device)
    swap0 = DS.swap_mb()
    rp = out_dir(root) / "rows" / f"build-{args.device}-{os.getpid()}.jsonl"
    rp.parent.mkdir(parents=True, exist_ok=True)
    t0 = started = time.time()
    with open(rp, "a") as fh:
        for m, i in enumerate(jobs):
            g = DS._guards("t3bk-build", T.DISK_GUARD_GB, swap0)
            if g:
                print(g[1], flush=True)
                raise SystemExit(g[0])
            sp = feat_path(root, i, "stem")
            if sp.exists() and sp.stat().st_mtime >= started:
                continue                                    # another worker's, written during this run
            e, x = ent[i], A.t2[i]
            tracks = backing_of(x, e["new"]["v"], e["new"]["n"])
            if tracks != entry_backing(e):
                raise SystemExit(f"{i}: the backing differs from the plan's")
            base = {"i": i, "set": e["set"], "section": e["section"], "band": e["band"], "device": args.device,
                    "backing_sha": tracks_sha(tracks), "plan_sha": psha}
            made = A.mix(i, tracks)
            if made is None:
                fh.write(json.dumps({**base, "refused": "no backing: the drawn ratio cannot be met"}) + "\n")
                fh.flush()
                continue
            y, mix, gains, lb = made
            s = _separate(sep, mix, i)
            mm, ml, _ = DS.half_features(mix)
            sm, sl, floor = DS.half_features(s)
            DS._save_npz(feat_path(root, i, "mix"), mA=mm["A"], mB=mm["B"], lufs=[ml["A"], ml["B"]],
                         gain_db=gains["ga"], mastered=x["draw"]["mastered"])
            DS._save_npz(sp, sA=sm["A"], sB=sm["B"], lufs=[sl["A"], sl["B"]])
            fh.write(json.dumps({**base, "vocals": e["vocals"], "stems": len(e["new"]["n"]), "gains_db": gains,
                                 "lufs_backing": lb, "lufs_mA": ml["A"], "lufs_mB": ml["B"], "lufs_sA": sl["A"],
                                 "lufs_sB": sl["B"], "floor_share": floor,
                                 "snr_audio_db": DS.snr_db(s, y * 10 ** (gains["ga"] / 20))}) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
            if m % 25 == 0:
                print(f"build {m + 1}/{len(jobs)}: {(time.time() - t0) / (m + 1):.1f} s per example", flush=True)
    print(f"BUILD DONE {ARM} ({args.device})")


def build_problems(root, p):
    """Changed examples not built from the plan's backing (or refused): -> list of (id, why)."""
    have, psha = rows(root, "build"), plan_sha(root)
    bad = []
    for e in p["examples"]:
        if e["same"] or e["left_out"]:
            continue
        r = have.get(e["i"])
        if r is not None and r.get("refused"):
            bad.append((e["i"], r["refused"]))
        elif not row_current(r, tracks_sha(entry_backing(e)), psha) or not feat_path(root, e["i"], "stem").exists():
            bad.append((e["i"], "not built from the plan's backing"))
    return bad


def cmd_check(args):
    require_bk(args)
    root = V.out_root(args)
    p = load_bk_plan(root, args.smoke)
    ctl = control_passed(root, p)
    bad = build_problems(root, p)
    print(f"control: {len(p['control']) - len(ctl)}/{len(p['control'])} passed; builds: "
          f"{sum(1 for e in p['examples'] if not e['same'] and not e['left_out']) - len(bad)} done, {len(bad)} open")
    for i, why in bad[:10]:
        print(f"  {i}: {why}")
    if ctl or bad:
        raise SystemExit("not complete")
    print(f"CHECK DONE {ARM}")


def cmd_train(args):
    """One D_F5bk run: `trusted_data_t3.cmd_train`'s D_F5 recipe on the new inputs; refuses unless every changed
    example is built, none refused, none left out, and its examples are D_F5's."""
    import numpy as np
    import torch

    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import pretrain_set as PS
    from learn import trusted_data_t3_mix as TM

    require_bk(args)
    root = V.out_root(args)
    if args.seed not in T3.TRAIN_SEEDS and not args.smoke:
        raise SystemExit(f"--seed in {T3.TRAIN_SEEDS}")
    rp = run_path(root, args.seed)
    if rp.exists():
        print(f"{rp.name} exists: nothing to do")
        return
    p = load_bk_plan(root, args.smoke)
    plan, drift = TM.load_frozen(root, args.smoke)
    ctx = DS.Ctx(quiet=True)
    tr_rows, es_rows = T3.arm_rows(root, ctx, plan, T3.FULL)
    f5_why = TM.same_examples(_load(T3.run_path(root, T3.FULL, args.seed)) or {}, p["refused_in_t3"], len(tr_rows),
                              len(es_rows))
    why = train_refusals(p, rows(root, "build"), rows(root, "control"), lambda i: feat_path(root, i, "stem").exists(),
                         plan_sha(root), [r["i"] for r in tr_rows], [r["i"] for r in es_rows], f5_why)
    if why and not args.smoke:
        raise SystemExit(f"{ARM} refuses to train: {len(why)} problems, e.g. {why[:5]}")
    ent = {e["i"]: e for e in p["examples"]}
    rows_ = tr_rows + es_rows
    files = {r["i"]: files_for(ent[r["i"]], root) for r in rows_}
    tr, es = np.arange(len(tr_rows)), np.arange(len(tr_rows), len(rows_))
    torch.set_num_threads(2)
    dev = torch.device("cpu" if os.environ.get("DS_DEVICE") == "cpu" or not torch.backends.mps.is_available()
                       else "mps")
    data = T.ArmData(rows_, files, aug=True, encode=T3.encode_for(T3.FULL), partner_path=T3.partner_path(root, T3.FULL))
    print(f"T3 {ARM} seed {args.seed}: {len(tr)} train, {len(es)} early stopping (FS5), "
          f"{sum(1 for e in p['examples'] if not e['same'])} with a new backing; {dev}", flush=True)
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
                raise SystemExit(f"TRAIN FAILED {ARM} {args.seed}: {e}")
    rp.parent.mkdir(parents=True, exist_ok=True)
    mp = rp.with_suffix(".pt")
    torch.save(state, mp)
    _save(rp, {"plan": PLAN, "stage": f"T3 {ARM}", "ledger": f"{T3.LEDGER_ID} {LEDGER_KEY}", "arm": ARM,
               "seed": args.seed, "model_arm": T.MODEL_ARM, "stem_sep": T.SEP, "augmented": True,
               "labels": "115 (full space, masked; amp head)", "train": len(tr), "early_stop": len(es),
               "new_backing": sum(1 for e in p["examples"] if not e["same"]), "dropped": p["refused_in_t3"],
               "attempts": attempt, "epochs_run": len(log), "best_epoch": best_ep, "best_early_stop_loss": best,
               "minutes": round((time.time() - t0) / 60, 1), "augmentations_applied": data.applied,
               "device": str(dev), "model": mp.name, "model_sha256": DS.hashlib_file(mp), "log": log,
               "drift": drift, "smoke": bool(args.smoke), "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"TRAIN DONE {ARM} {args.seed}: best epoch {best_ep} of {len(log)}")
    if best_ep is not None and best_ep >= DS.MAX_EPOCHS - T3.CAP_EDGE:
        print(f"WARNING: best epoch {best_ep} is within {T3.CAP_EDGE} of the cap {DS.MAX_EPOCHS}: extend this run "
              "before it is read")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="trusted_data_t3_bk", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("plan", cmd_plan), ("control", cmd_control), ("build", cmd_build), ("check", cmd_check),
                     ("train", cmd_train)):
        s = sub.add_parser(name)
        s.set_defaults(fn=fn)
        s.add_argument("--out", default=None)
        s.add_argument("--smoke", action="store_true")
        if name == "plan":
            s.add_argument("--dry", action="store_true")
        if name in ("control", "build"):
            s.add_argument("--device", choices=DEVICES, required=True)
        if name == "build":
            s.add_argument("--order", choices=("asc", "desc"), default="asc")
            s.add_argument("--limit", type=int, default=0)
        if name == "train":
            s.add_argument("--seed", type=int, required=True)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
