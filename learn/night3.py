"""N5 (`docs/pipeline-fix-plan.md`, ledger `phase_n5`): does the reading survive the stem? Zero plugin renders.

FTm and the other models train and read on a real unit in a backing (`build-dfix-real`'s variant 0). The product reads an
X-LANCE stem. Here each labelled BKS and GOAT unit's variant 0 mix is rebuilt, checked against its stored features to the
last value, and separated, so the same held read can run on the stem. -> night3/audio/<unit>.npz, night3/inputs/<unit>.npz.

    $MSST -u -m learn.night3 build --device mps [--limit n]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import pathlib

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

PHASE = "phase_n5"


def root():
    from learn import pipeline_fix as P

    return P.out_dir() / "night3"


def name_of(unit):
    return unit.replace("/", "__")


def rebuild(unit, kind, prt, env):
    """A unit's variant 0 mix, by `cmd_build_dfix_real`'s recipe; the caller checks it against the stored features."""
    import numpy as np

    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import cc_build as CB
    from learn import pipeline_fix as P
    from learn import song_aug as SA
    from learn import trusted_data as T

    kept, rend, sp, built, stems, pool, own_lv, croot = (env[k] for k in ("kept", "rend", "sp", "built", "stems", "pool", "own_lv", "croot"))
    bks = kind == "bks"
    d0 = np.load(P.dfix_input_path(unit, 0))
    i, rule = P.dfix_lend(unit, prt["cls"], sp["train"], kept, prt["section"] if bks else None)
    if int(d0["lend"]) != i:
        raise SystemExit(f"{unit}: lent by {int(d0['lend'])}, the rule gives {i}")
    x, rw, bw = kept[i], rend[i], built[i]
    e_voc = bool(x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"])
    y = np.asarray(G.read_flac(T.flac_path(croot, CB.STAGE, i, "target"), rw["target"]["scale"], rw["target"]["sha256"]), np.float64)
    tl = float(SA.lufs(y))
    ref = np.asarray(P.real_amp_track(prt["sd"], prt["track"], prt["start_s"]), np.float64)
    gtr, _ = P.dfix_level(ref, tl, SA.lufs)
    e_lv = own_lv[x["section"]][str(e_voc)]
    j, voc = P.dfix_draws(unit, prt["section"], pool, own=bks)[0]
    if j is None:
        own_x = x if rule == "section" else kept[min(q for q in kept if kept[q]["section"] == prt["section"])]
        tracks = P.bare_tracks(own_x, e_voc)
        voc = bool(e_voc and own_x["stems"]["v"] != own_x["stems"]["n"])
        back = np.asarray(stems.get(prt["section"], tracks), np.float64)
        lv = own_lv[prt["section"]][str(voc)] if rule == "section" else float(SA.lufs(back))
    else:
        ent = pool[j]
        tracks = ent["tracks"]["v" if voc else "n"]
        back = np.asarray(stems.get(ent["id"], tracks) if ent["kind"] == "training"
                          else P.bare_backing(ent["sd"], tracks, ent["start_s"]), np.float64)
        lv = ent["lufs"][str(bool(voc))]
    gb, ga = P.dfix_backing_gain(bw["gains_db"]["gb"], e_lv, lv), bw["gains_db"]["ga"]
    mix = P.dfix_mix(gtr, back, gb, ga)
    mastered, mrng = DS.master_draw(i)
    if mastered:
        mix = SA.compress(mix, mrng)
    return mix


def cmd_build(args):
    import numpy as np

    from learn import cc_build as CB
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import pipeline_fix as P
    from learn import trusted_data as T

    P.require(PHASE)
    e = P.require("phase_dfix")
    croot, kept, rend, sp, _ = P.recipe_inputs(pin=e.get("phase_3_doubles"))
    a = argparse.Namespace(out=None, smoke=False)
    env = {"kept": kept, "rend": rend, "sp": sp, "croot": croot, "built": T.rows_of(croot, CB.STAGE, "build"), "stems": T.Stems(CB.ctx_for(a)),
           "pool": json.loads(P.wide_pool_path().read_text())["entries"],
           "own_lv": json.loads((P.out_dir() / "inputs" / "backings-levels.json").read_text())["levels"]}
    target = P.vreal_mix_target()
    units = [u for u in P.dfix_units() if not (root() / "inputs" / f"{name_of(u[0])}.npz").exists()]
    units = units[:args.limit or None]
    print(f"night3 build: {len(units)} units on {args.device}", flush=True)
    sep = DS.stem_separator(T.SEP, args.device)
    swap0 = DS.swap_mb()
    (root() / "inputs").mkdir(parents=True, exist_ok=True)
    (root() / "audio").mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for m, (unit, kind, prt) in enumerate(units):
        g = DS._guards("night3-build", T.DISK_GUARD_GB, swap0)
        if g:
            print(g[1], flush=True)
            raise SystemExit(g[0])
        mix = rebuild(unit, kind, prt, env)
        d0 = np.load(P.dfix_input_path(unit, 0))
        f, lu, _ = DS.half_features(mix)
        if not (np.array_equal(f["A"], d0["sA"]) and np.array_equal(f["B"], d0["sB"])):
            raise SystemExit(f"{unit}: the rebuilt mix is not variant 0's")
        stem = np.asarray(sep(mix), np.float64)
        if len(stem) != len(mix) or not np.isfinite(stem).all():
            raise SystemExit(f"{unit}: bad stem")
        gain = DE.inference_gain_db(mix, target)
        (sA, _, la, _), (sB, _, lb, _) = (DS.step4_half(stem, mix, h, gain) for h in ("A", "B"))
        np.savez(root() / "audio" / f"{name_of(unit)}.npz", mix=np.asarray(mix, np.float32), stem=stem.astype(np.float32))
        DS._save_npz(root() / "inputs" / f"{name_of(unit)}.npz", sA=sA, sB=sB, lufs=[la, lb], gain_db=gain, kind=kind)
        if m % 25 == 0:
            print(f"night3 {m + 1}/{len(units)}: {(time.time() - t0) / (m + 1):.1f} s each", flush=True)
    print("NIGHT3 BUILD DONE", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--device", default="mps")
    b.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)
    {"build": cmd_build}[args.cmd](args)


if __name__ == "__main__":
    main()
