"""N4 (`docs/pipeline-fix-plan.md`, ledger `phase_n4`): masked FT by ear on L0's 10 parts, beside S and FT.

The page is L0's in three letters: the same parts, directions, measure DI and held windows. S's and FT's clips are L0's stored
renders; only FTm is rendered. It picks nothing: a lead for L2, at least V-real's fifth read.

    $TORCH -m learn.ear_ftm answers            # all-labels FTm on L0's 10 directions, X-LANCE stems as read 3 (zero renders)
    $MAIN  -m learn.ear_ftm render --shard k/n # FTm through each part's measure DI, hash and judge stored
    $MAIN  -m learn.ear_ftm page               # -> ~/ndsp-presets/listening/ear-ftm/index.html
    $MAIN  -m learn.ear_ftm score --answers FILE
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import secrets
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from learn import capture_ear as C           # noqa: E402
from learn import ear_vreal as E             # noqa: E402

PHASE = "phase_n4"
PAGE_SEED = 20261110
ROLE = {"S": "S", "FTm": "label", "FT": "placebo"}      # the report's rows: label is FTm, placebo FT


def data_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / "ear-ftm"


def page_dir():
    from learn import pretrain_set as PS

    return PS.HOME / "listening" / "ear-ftm"


def units():
    """L0's 10 parts, one direction each, as declared there."""
    return json.loads((E.data_dir() / "plan.json").read_text())["units"]


def load_nets():
    from learn import pipeline_fix as P

    nets, recs = [], []
    for sd in P.SEEDS:
        net, rec = P.load_run(P.FTM_BASE, sd, "best")
        P.ft_read_check(rec)
        if rec["real_fold"] is not None or not rec.get("masked"):
            raise SystemExit(f"{P.FTM_BASE}-{sd}: not the all-labels masked run")
        nets.append(net)
        recs.append(rec)
    if recs[0]["train_ids"] != recs[1]["train_ids"]:
        raise SystemExit(f"{P.FTM_BASE}: both seeds on one training set")
    return nets, recs


def cmd_answers(_args):
    from learn import direct_stems as DS
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pipeline_review as PR
    from learn import trusted_data as T

    P.require(PHASE)
    root, plan, drift, dirs, parts, ms = P.vreal_ctx()
    nets, recs = load_nets()
    target = P.vreal_mix_target()
    man = DS._load(DS.stems_manifest_path(DS.ROOT, T.SEP))
    out = {}
    for u in units():
        slug, amp, search = u["slug"], u["amp"], u["search"]
        cls = PR.VREAL[slug][1]
        sel, S = ms[amp][cls]
        stem, mix, g, _ = P.vreal_stem_input(man, slug, parts[slug], target)
        s8, _, ls, _ = DS.step4_half(stem, mix, search, g)
        x, c = P.vreal_model_input(s8, ls, search, amp, cls)
        r = F.readout([o[0] for o in F.run_nets(nets, [x], [c])])
        st = P.hold_outside_space(F.answer_settings(amp, S, r["a2"], r["sw_p"], r["mics"]), S, amp)
        out[f"{slug}|{amp}"] = {"select": sel, "settings": LO.sdict(st)}
    P.save(data_dir() / "answers.json", {"phase": PHASE, "model": P.FTM_BASE, "E": recs[0]["E"], "answers": out,
                                         "model_sha256": [r["model_sha256"]["best"] for r in recs],
                                         "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"EAR-FTM ANSWERS DONE: {len(out)} parts")


def cmd_render(args):
    """FTm through each part's measure DI, in L0's recipe (a fresh process, one priming render), the held window kept."""
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import rescore as R
    from learn import trusted_data as T
    from learn import trusted_data_t3 as T3

    P.require(PHASE)
    k, n = (int(x) for x in args.shard.split("/"))
    ans = json.loads((data_dir() / "answers.json").read_text())["answers"]
    root, plan, drift, dirs, parts, ms = P.vreal_ctx()
    LO._wait_cap()
    rr = CB.new_renderer()
    try:
        menu = rr.menu()
    finally:
        rr.close()
    renders = 0
    for u in [u for j, u in enumerate(units()) if j % n == k]:
        slug, amp, held = u["slug"], u["amp"], u["held"]
        out = data_dir() / "renders" / slug
        if (out / "rec.json").exists():
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        info = parts[slug]
        ctx = (A.group_ctx(menu, ms, "F", slug, amp) if info["kind"] == "stagef" else T3.t3_group_ctx(menu, ms, info, amp))
        lag = ctx["part"]["judge_lag"]
        a, b = (int(x * E.SR) for x in R.HALVES[held])
        got = ans[f"{slug}|{amp}"]
        st = LO.tdict(got["settings"])
        y = AM.fresh_render(CB.new_renderer, ctx["di32"], got["select"], st, st)
        renders += 2
        mono = y.mean(axis=1) if y.ndim == 2 else y
        rec0 = json.loads((E.data_dir() / "renders" / slug / "rec.json").read_text())
        s0, s1 = rec0["window"]
        d = K.judge(ctx["ref"], np.asarray(mono, np.float64), np.asarray(ctx["di32"], np.float64)[:len(mono)], lag)
        out.mkdir(parents=True, exist_ok=True)
        np.savez(out / "clips.npz", FTm=mono[s0 - lag:s1 - lag].astype(np.float32))
        P.save(out / "rec.json", {"slug": slug, "amp": amp, "held": held, "lag": lag, "window": [s0, s1], "judge": d[held],
                                  "sha": AM.audio_sha(y), "window_check": list(E.window(a, b, len(ctx["ref"]), len(mono), lag))})
        print(f"{slug} {amp}: renders so far {renders}", flush=True)
    print(f"EAR-FTM RENDER DONE {k}/{n}: {renders} renders")


def cmd_page(_args):
    import numpy as np

    from learn import pipeline_fix as P

    P.require(PHASE)
    key_path = data_dir() / "key.json"
    if key_path.exists():
        raise SystemExit(f"{key_path} exists: a rebuild hides the listener's stored answers; move it aside first")
    root, _, _, _, parts, _ = P.vreal_ctx()
    rows = [{"unit": u["slug"], "slug": u["slug"], "band": u["band"], "creator": u["band"], "cls": u["cls"], "amp": u["amp"]}
            for u in units()]
    items = C.draw(rows, PAGE_SEED)
    cache, od = data_dir() / "aac-cache", page_dir()
    od.mkdir(parents=True, exist_ok=True)
    clips, kept = {}, []
    for it in items:
        d0 = E.data_dir() / "renders" / it["slug"]
        rec0 = json.loads((d0 / "rec.json").read_text())
        rec = json.loads((data_dir() / "renders" / it["slug"] / "rec.json").read_text())
        z0, z = np.load(d0 / "clips.npz"), np.load(data_dir() / "renders" / it["slug"] / "clips.npz")
        s0, s1 = rec0["window"]
        ref = np.asarray(P.amp_track(it["slug"], parts[it["slug"]]), np.float64)[s0:s1]
        have = {"S": z0["S"], "FT": z0["FT"], "FTm": z["FTm"]}
        by_role = {"S": have["S"], "label": have["FTm"], "placebo": have["FT"]}
        group = {"ref": ref, **{k: np.asarray(by_role[c], np.float64) for k, c in it["letters"].items()}}
        if len({len(v) for v in group.values()}) != 1:
            raise SystemExit(f"{it['slug']}: clip lengths differ")
        lev, info = E.level_group(group)
        for k, y in lev.items():
            clips[f"{it['id']}-{k}"] = E.encode(y, cache)
        kept.append({**it, "judge": {"S": rec0["judge"]["S"], "placebo": rec0["judge"]["FT"], "label": rec["judge"]}, "levels": info})
    build = hashlib.sha256((json.dumps([k["letters"] for k in kept]) + secrets.token_hex(8)).encode()).hexdigest()[:12]
    body = C.cards(kept)
    data = json.dumps({"build": build, "items": [{"id": it["id"], "n": it["n"]} for it in kept]})
    a, b = E.PAGE.index("<h1>"), E.PAGE.index("@@CARDS@@")
    intro = C.INTRO.replace("a guitar through a captured real amp", "the guitar as it was recorded through a real amp")
    page = (E.PAGE[:a] + intro + "\n" + E.PAGE[b:]).replace("@@COUNT@@", str(len(kept))).replace("@@CARDS@@", body) \
        .replace("@@CSS@@", E.CSS + ".rank.three { grid-template-columns:auto repeat(3, 1fr); }") \
        .replace("@@DATA@@", data).replace("@@CLIPS@@", json.dumps(clips)).replace("@@JS@@", C.page_js().replace("capture-labels", "ear-ftm"))
    if C.page_leaks([{"unit": k["slug"], "creator": k["band"]} for k in kept], body, data):
        raise SystemExit("the page names a part or a band")
    P.save(key_path, {"page": "ear-ftm", "build": build, "phase": PHASE, "items": kept, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    (od / "index.html").write_text(page)
    print(f"EAR-FTM PAGE DONE: {len(kept)} items -> {od / 'index.html'}; build {build}")


def cmd_score(args):
    from learn import pipeline_fix as P

    P.require(PHASE)
    key = json.loads((data_dir() / "key.json").read_text())
    last = [ln for ln in pathlib.Path(args.answers).read_text().splitlines() if ln.startswith("{")][-1]
    ex = json.loads(last)
    if ex.get("build") != key["build"]:
        raise SystemExit(f"{args.answers}: build {ex.get('build')}, this page's is {key['build']}")
    heard = {it["id"]: C.unblind(it, ex["answers"].get(it["id"]) or {}) for it in key["items"]}
    unsure = [it["id"] for it in key["items"] if (ex["answers"].get(it["id"]) or {}).get("conf") == "unsure"]
    rep = C.report(key["items"], heard, unsure)
    rep.update(build=key["build"], roles=ROLE, answered=sum(v is not None for v in heard.values()), items=len(key["items"]), unsure=unsure)
    P.save(data_dir() / "score.json", rep)
    print(json.dumps(rep, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("answers")
    sub.add_parser("page")
    r = sub.add_parser("render")
    r.add_argument("--shard", default="0/1")
    s = sub.add_parser("score")
    s.add_argument("--answers", required=True)
    args = ap.parse_args(argv)
    {"answers": cmd_answers, "render": cmd_render, "page": cmd_page, "score": cmd_score}[args.cmd](args)


if __name__ == "__main__":
    main()
