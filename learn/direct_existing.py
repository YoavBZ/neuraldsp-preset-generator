"""Part C's existing direct model on stage F, and the yardstick-cap check
(`docs/direct-existing-plan.md`). Development only; no training. Estimates with 90%
band-clustered intervals, no pass/fail bars.

    .venv/bin/python -m learn.direct_existing parity                  # zero renders: the inference path against stored features
    $TORCH_PY -m learn.direct_existing predict                        # zero renders: D_existing's settings for the 126 directions
    OMP_NUM_THREADS=1 .venv/bin/python -m learn.direct_existing render --shard i/3
    .venv/bin/python -m learn.direct_existing report

TORCH_PY is ~/ndsp-presets/tools/demucs-venv/bin/python. Outputs go to
~/ndsp-presets/learn/direct-existing/.

Test 1: D_existing (part C's three 40k curve models, ensembled) predicts settings from each stage F
direction's search half (the stored full-mix crop and its stored htdemucs stem, hash-checked), as
part C's val inputs were built; each prediction is rendered once through the part's measure DI and
judged on the held half, paired with the stored S, H and XO.

Test 2: S, H, XO and D_existing re-judged through the part's raw DI (`di.wav`, one gain to −22.9
LUFS, no average-guitar EQ); on the known-answer songs, S and the truth judged through the
per-section measure DI and the raw DI (the truth's own DI), all primed.

The pure parts (the ensemble, the settings, the features' masking and gain, the rows, the counts,
the sharding) are unit-tested (`tests/test_direct_existing.py`); the commands that render or load
models are not, like the other step modules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import sys
import time

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

HOME = pathlib.Path("~/ndsp-presets").expanduser()
OUT = HOME / "learn/direct-existing"
CURVE_MODELS = HOME / "learn/pretrain-set/curve-models"
MODEL_N = 40_000
SEEDS = (20261042, 20261043, 20261044)
LEVELS = HOME / "learn/song-settings/bank/levels.json"
KA = HOME / "learn/known-answer/b1"
REPEAT_TOL = 1e-3                     # |log| of S's fresh measure-DI judge against the stored one
PARITY_N = 20                         # audit examples in the parity check
PARITY_CELL_SHARE = 0.99              # share of mel cells within one 0.5-dB step
PARITY_LUFS_TOL = 0.01                # LU
RAW_LUFS = -22.9
PER_GROUP = 3 + 8                     # measure: priming, S, D x2; raw: priming, S, H x2, XO x2, D x2
PER_KA_SECTION = 6                    # raw: priming, S, truth; measure: priming, S, truth
CAP = 900
ARMS_RAW = ("S", "H", "XO", "D")
CONTRASTS = (("D", "S"), ("D", "H"), ("D", "XO"), ("H", "S"), ("XO", "S"), ("XO", "H"))
ROWS = ("all", "no_high_dir", "f_song", "unseen_by_part_c")


def _save(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    tmp.replace(path)


def _load(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.exists() else None


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def model_paths():
    return [CURVE_MODELS / f"{MODEL_N}-{s}.pt" for s in SEEDS]


# --- the ensemble (pure) -----------------------------------------------------------------------------

def ensemble(outs):
    """outs: per seed (logpi [K], mu [K, n], switch logits [n_sw], [mic logits per cat dim]) as
    plain lists or arrays. -> (cont [n], switches [n_sw] bool, mics [n_cat] int, diag).
    Continuous: the mean of the highest-weight component of the pooled mixture (each seed's
    weights / number of seeds); switches: the majority of the seeds (p > 0.5); mics: the argmax of
    the summed probabilities."""
    import numpy as np

    n_s = len(outs)
    best, bw = None, -1.0
    for s, (logpi, mu, _, _) in enumerate(outs):
        w = np.exp(np.asarray(logpi, np.float64)) / n_s
        k = int(np.argmax(w))
        if w[k] > bw:
            best, bw = (s, k), float(w[k])
    s, k = best
    cont = np.clip(np.asarray(outs[s][1], np.float64)[k], 0.0, 1.0)
    votes = np.sum([1.0 / (1.0 + np.exp(-np.asarray(o[2], np.float64))) > 0.5 for o in outs], axis=0)
    sw = votes * 2 > n_s
    mics = []
    for j in range(len(outs[0][3])):
        p = np.zeros(len(outs[0][3][j]))
        for o in outs:
            z = np.asarray(o[3][j], np.float64)
            e = np.exp(z - z.max())
            p += e / e.sum()
        mics.append(int(np.argmax(p)))
    tops = [np.asarray(o[1], np.float64)[int(np.argmax(o[0]))] for o in outs]
    diag = {"seed": SEEDS[s] if n_s == len(SEEDS) else s, "component": k, "pooled_weight": bw,
            "seed_spread": float(np.mean([np.abs(t - cont).mean() for t in tops]))}
    return cont, sw, mics, diag


def settings_from(amp, S, cont, sw, mics, space, fmt, layout):
    """S's settings with the labelled dimensions replaced, as part C labels them.
    layout: (CONT, SW, CAT, MICS) of `song_model`."""
    CONT, SW, CAT, MICS = layout
    x = dict(S)
    dims = {d.name: d for d in space(amp, S)}
    for i, n in enumerate(CONT):
        if n in dims:
            d = dims[n]
            x[(d.module, d.key)] = fmt(d.from_unit(float(cont[i])))
    for i, n in enumerate(SW):
        if n in dims:
            d = dims[n]
            x[(d.module, d.key)] = d.values[int(bool(sw[i]))]
    for j, n in enumerate(CAT):
        if n in dims:
            d = dims[n]
            x[(d.module, d.key)] = MICS[int(mics[j])]
    return x


# --- features (the inference path) -------------------------------------------------------------------

def mono(y):
    import numpy as np

    y = np.asarray(y, np.float64)
    return y.mean(axis=1) if y.ndim == 2 else y


def features(mix, stem, half, gain_db):
    """One half's model input as part C's val inputs are built: both channels times one gain,
    arm B's log-mel quantised to the stored 0.5-dB grid, normalised, half A's first second masked;
    the conditioning LUFS are the half's stem and mix LUFS after the gain.
    -> (x [2, 96, frames] float32, [lufs_stem, lufs_mix])."""
    import numpy as np

    from learn import pretrain_set as PS
    from learn import song_aug as SA
    from learn import song_model as SM

    k = 10 ** (gain_db / 20)
    sl = PS.half_slices()[half]
    m, s = mono(mix)[sl] * k, mono(stem)[sl] * k
    q = np.stack([PS.dequant(PS.quant(SA.logmel(s))), PS.dequant(PS.quant(SA.logmel(m)))])
    x = PS.mask_half_a(SM.norm_feat(q)[None], [half == "A"])[0]
    return x.astype(np.float32), [SA.lufs(s), SA.lufs(m)]


def inference_gain_db(mix, target):
    """The one gain that brings the 10-s crop's mix to the training median."""
    from learn import song_aug as SA

    return target - SA.lufs(mono(mix))


# --- stage F's inputs --------------------------------------------------------------------------------

def f_inputs(slug):
    """(mix crop, htdemucs stem crop, hashes): the stored context's crop slice (asserted equal to the
    crop folder's mix.wav) and the stored stem crop."""
    import numpy as np
    import soundfile as sf

    from learn import arm_a_mega53 as A

    log = json.loads(A.fdir("contexts", "log.json").read_text())[slug]
    ctx_p = A.fdir("contexts", f"{slug}.npy")
    stem_p = A.sep_crop("htdemucs", slug)
    ctx = np.load(ctx_p)
    mix = mono(ctx)[log["offset"]:log["offset"] + A.CROP]
    crop, _ = sf.read(str(A.f_part(slug)["crop"] / "mix.wav"), dtype="float64")
    if len(mix) != A.CROP or float(np.max(np.abs(mix - mono(crop)))) > 1e-6:
        raise SystemExit(f"{slug}: the context's crop slice is not the crop's mix.wav")
    stem = mono(np.load(stem_p))
    if len(stem) != A.CROP:
        raise SystemExit(f"{slug}: stem crop has {len(stem)} samples")
    return mix, stem, {"context": sha256(ctx_p), "stem": sha256(stem_p)}


def unseen_bands(pool_sections):
    """Stage F bands with no part C training or early-stopping section (val and reserve are not
    trained on)."""
    from learn import arm_a_mega53 as A

    trained = {s["band"] for s in pool_sections if s["split"] == "train"}
    return sorted(b for b in A.F_POOL if b not in trained)


# --- the counts and the shards (pure) ----------------------------------------------------------------

def expected_renders(n_groups=63, n_ka=16):
    return n_groups * PER_GROUP + n_ka * PER_KA_SECTION


def shard(xs, sh):
    return sorted(xs)[sh[0]::sh[1]]


def ka_sections():
    from learn import known_answer as KAM

    return [(song, lab) for song in sorted(KAM.SONGS) for lab in ("s1", "s2", "s3", "s4")]


# --- commands ----------------------------------------------------------------------------------------

def cmd_parity(_args):
    """Zero renders: audit train examples (whose render audio is stored) rebuilt into their mix and
    stem at the stored gains, through `features` with the stored overall gain; against the stored
    uint8 features and LUFS."""
    import numpy as np
    import soundfile as sf

    from learn import pretrain_set as PS

    rows = [r for r in PS.all_rows().values() if r.get("audit") and "mix" in r]
    rows = sorted(rows, key=lambda r: r["i"])[:PARITY_N]
    out = []
    for r in rows:
        f = PS.example_path(r["i"]).with_suffix(".flac")
        y, _ = sf.read(str(f), dtype="float64")
        y = y / 0.99 * r["peak"]
        b, _ = PS.load_backing_audio(r["section"], "v" if r["mix"]["vocals"] else "n")
        gb, gl, ga = r["mix"]["gains_db"]
        mix0, stem0 = y + b * 10 ** (gb / 20), y + b * 10 ** (gl / 20)
        d = np.load(PS.example_path(r["i"]))
        for h in "AB":
            x, lu = features(mix0, stem0, h, ga)
            for c, key, lk in ((0, f"s{h}", f"lufs_s{h}"), (1, f"m{h}", f"lufs_m{h}")):
                stored = PS.dequant(d[key])
                mine = x[c] * 30.0 - 60.0
                keep = np.ones(stored.shape, bool)
                if h == "A":
                    keep[:, :PS.MASK_A_FRAMES] = False
                diff = np.abs(mine - stored)[keep]
                out.append({"i": r["i"], "half": h, "channel": "stem" if c == 0 else "mix",
                            "share_within_step": float(np.mean(diff <= PS.Q_STEP_DB + 1e-6)),
                            "max_diff_db": float(diff.max()), "lufs_diff": abs(lu[c] - r["mix"][lk])})
    worst = min(o["share_within_step"] for o in out)
    lufs_worst = max(o["lufs_diff"] for o in out)
    ok = worst >= PARITY_CELL_SHARE and lufs_worst <= PARITY_LUFS_TOL
    _save(OUT / "parity.json", {"ok": ok, "examples": len(rows), "worst_share_within_step": worst,
                                "worst_lufs_diff": lufs_worst, "rows": out})
    print(f"parity: {len(rows)} examples; worst share within one step {worst:.5f}; worst LUFS diff {lufs_worst:.4f};",
          "ok" if ok else "FAIL")
    if not ok:
        raise SystemExit(1)


def cmd_predict(_args):
    """Zero renders: the ensemble's settings for stage F's 126 directions."""
    import numpy as np
    import torch

    from learn import arm_a_mega53 as A
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pretrain_set as PS
    from learn import song_model as SM

    if not (_load(OUT / "parity.json") or {}).get("ok"):
        raise SystemExit("run `parity` first")
    torch.set_num_threads(2)
    nets, mhash = [], {}
    for p in model_paths():
        net = PS.build_net()
        net.load_state_dict(torch.load(p, map_location="cpu"))
        nets.append(net.eval())
        mhash[p.name] = sha256(p)
    target = json.loads(LEVELS.read_text())["summary"]["eval_mix_lufs_median"]
    ms = A.L.menu_S()
    pool = json.loads((PS.OUT / "pool.json").read_text())
    preds, inputs = {}, {}
    for slug, amp, search, held in A.stage_dirs("F"):
        part = A.f_part(slug)
        if slug not in inputs:
            mix, stem, hashes = f_inputs(slug)
            inputs[slug] = {"mix": mix, "stem": stem, "hashes": hashes, "gain_db": inference_gain_db(mix, target)}
        it = inputs[slug]
        x, lu = features(it["mix"], it["stem"], search, it["gain_db"])
        c = SM.cond_vec(amp, part["gain_class"], lu)
        outs = []
        with torch.no_grad():
            for net in nets:
                logpi, mu, _, swl, catl = net(torch.tensor(x[None]), torch.tensor(c[None]))
                outs.append((logpi[0].numpy(), mu[0].numpy(), swl[0].numpy(), [z[0].numpy() for z in catl]))
        cont, sw, mics, diag = ensemble(outs)
        _, S = ms[amp][part["gain_class"]]
        xs = settings_from(amp, S, cont, sw, mics, K.space, K.fmt, (SM.CONT, SM.SW, SM.CAT, SM.MICS))
        preds[f"{slug}|{amp}|{search}"] = {"settings": LO.sdict(xs), "diag": diag, "cond_lufs": lu,
                                          "gain_db": it["gain_db"], "held": held}
    rec = {"models": mhash, "target_mix_lufs": target, "inputs": {s: v["hashes"] for s, v in inputs.items()},
           "unseen_by_part_c": unseen_bands(pool["sections"]), "predictions": preds,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    _save(OUT / "predictions.json", rec)
    sp = [p["diag"]["seed_spread"] for p in preds.values()]
    print(f"predict: {len(preds)} directions; seed spread median {float(np.median(sp)):.4f}; "
          f"unseen bands {rec['unseen_by_part_c']}")


def _stop(why):
    _save(OUT / "STOP.json", {"why": why, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    raise SystemExit(why)


def spent():
    return sum(int((_load(p) or {}).get("renders", 0)) for p in (OUT / "groups").rglob("*.json")) if OUT.exists() else 0


def cmd_render(args):
    """Stage F groups of this shard, then (shard 0) the known-answer sections. One process; a
    priming render at S after the start and every DI or amp change."""
    import numpy as np

    from learn import arm_a_mega53 as A
    from learn import confirm_run as CR
    from learn import knob_ceiling as K
    from learn import known_answer as KAM
    from learn import local_objective as LO
    from learn import song_bank as B
    from learn.direc_check import to_lufs

    if (OUT / "STOP.json").exists():
        raise SystemExit("STOP.json present")
    pred = _load(OUT / "predictions.json")
    if not pred or len(pred["predictions"]) != A.N_DIRS["F"]:
        raise SystemExit("run `predict` first")
    for p in model_paths():
        if sha256(p) != pred["models"][p.name]:
            raise SystemExit(f"{p.name} changed since predict")
    if spent() >= CAP:
        raise SystemExit("cap reached")
    groups = shard(A.groups(A.stage_dirs("F")), args.shard)
    LO._wait_cap()
    rr = A.renderer()
    ms = A.L.menu_S()
    try:
        menu = rr.menu()
        for slug, amp in groups:
            gp = OUT / "groups" / f"{slug}|{amp}.json"
            if (_load(gp) or {}).get("status") == "done":
                continue
            if not LO.disk_ok(LO.disk_free_gb(), 1):
                _stop("free disk below the guard")
            if spent() + PER_GROUP > CAP:
                _stop(f"cap {CAP}")
            _, _, hashes = f_inputs(slug)
            if hashes != pred["inputs"][slug]:
                _stop(f"{slug}: inputs changed since predict")
            ctx = A.group_ctx(menu, ms, "F", slug, amp)
            if K.key(dict(ctx["S"])) != K.key(ctx["S_stored"]):
                _stop(f"{amp}: the live S differs from the stored copy")
            part, sel, S, ref, lag = ctx["part"], ctx["sel"], ctx["S"], ctx["ref"], ctx["part"]["judge_lag"]
            n0 = rr.count
            rec = {"slug": slug, "amp": amp, "measure": {}, "raw": {}, "status": "running"}
            d = {sh: LO.tdict(pred["predictions"][f"{slug}|{amp}|{sh}"]["settings"]) for sh, _ in K.DIRECTIONS}
            # the measure DI: priming, S (the repeat check), D's two predictions
            dm, dm32 = ctx["di"], ctx["di32"]
            rr.render(dm32, sel, S)
            rec["measure"]["S"] = K.judge(ref, rr.render(dm32, sel, S), dm, lag)
            stored = json.loads(A.s_path(slug, amp).read_text())["judge"]
            dev = max(LO.deviation(rec["measure"]["S"][h], stored[h]) for h in ("A", "B"))
            rec["repeat_dev"] = dev
            if dev > REPEAT_TOL:
                _save(gp, {**rec, "renders": rr.count - n0, "status": "stopped"})
                _stop(f"{slug} {amp}: S's measure-DI judge moved {dev:.5f} from the stored")
            for sh, _ in K.DIRECTIONS:
                rec["measure"][f"D|{sh}"] = K.judge(ref, rr.render(dm32, sel, d[sh]), dm, lag)
            # the raw DI at −22.9 LUFS: priming, S, H, XO, D
            raw = to_lufs(CR.mono(part["crop"] / "di.wav"))
            raw32 = raw.astype(np.float32)
            rr.render(raw32, sel, S)
            rec["raw"]["S"] = K.judge(ref, rr.render(raw32, sel, S), raw, lag)
            for sh, _ in K.DIRECTIONS:
                h_ = json.loads(A.result_path("F", "H", slug, amp, sh).read_text())
                xo = json.loads((A.OUT / "F-oracle" / "XO" / slug / amp / f"{sh}.json").read_text())
                for arm, s_ in (("H", h_["settings"]["output"]), ("XO", xo["settings"]["output"])):
                    rec["raw"][f"{arm}|{sh}"] = K.judge(ref, rr.render(raw32, sel, LO.tdict(s_)), raw, lag)
                rec["raw"][f"D|{sh}"] = K.judge(ref, rr.render(raw32, sel, d[sh]), raw, lag)
            rec.update(renders=rr.count - n0, status="done", raw_lufs=LO.lufs(raw))
            _save(gp, rec)
            print(slug, amp, "repeat", f"{dev:.2e}", "D held", {sh: round(rec["measure"][f"D|{sh}"][h], 3)
                                                                for sh, h in K.DIRECTIONS}, rr.count, flush=True)
        if args.shard[0] == 0:
            tr = json.loads((KA / "truth" / "truth.json").read_text())
            for song, lab in ka_sections():
                kp = OUT / "groups" / "ka" / f"{song}-{lab}.json"
                if (_load(kp) or {}).get("status") == "done":
                    continue
                dr = tr[song]["draws"][KAM.truth_of(song, lab)]
                amp = dr["amp"]
                sel_s, S = menu[amp][K.START[KAM.s_class(dr["class"])][amp]]
                tx = LO.tdict(dr["settings"])
                d_ = np.load(KA / "truth" / f"{song}-{lab}-di.npy").astype(np.float64)
                rec_ = np.load(KA / "truth" / f"{song}-{lab}-record.npy").astype(np.float64)
                n0 = rr.count
                out = {"song": song, "label": lab, "amp": amp}
                for name, di in (("raw", d_), ("measure", B.measure(d_))):
                    di32 = di.astype(np.float32)
                    rr.render(di32, sel_s, S)
                    out[name] = {"S": K.judge(rec_, mono(rr.render(di32, sel_s, S)), di, KAM.RECORD_LAG),
                                 "truth": K.judge(rec_, mono(rr.render(di32, dr["select"], tx)), di, KAM.RECORD_LAG)}
                chk = tr[song]["checks"][lab]
                out["stored"] = {"raw_truth": chk["self"], "raw_S": chk["S_truth_amp"],
                                 "measure_truth": chk["convention_floor"]}
                out.update(renders=rr.count - n0, status="done")
                _save(kp, out)
                print("KA", song, lab, amp, {k: round(out[k]["truth"]["A"], 4) for k in ("raw", "measure")}, flush=True)
    finally:
        rr.close()
    print(f"RENDER DONE {args.shard[0]}/{args.shard[1]}; renders this process {rr.count}; spent {spent()}", flush=True)


# --- the report --------------------------------------------------------------------------------------

def build_units(groups_dir=None, stage_f=None):
    """Units per direction: d (measure judge: S, H, XO stored; D new) and d_raw (all new)."""
    from learn import arm_a_mega53 as A

    groups_dir = groups_dir or OUT / "groups"
    units = []
    for u in A.build_units("F", ("H",)):
        g = _load(groups_dir / f"{u['slug']}|{u['amp']}.json") or {}
        xo = _load(A.OUT / "F-oracle" / "XO" / u["slug"] / u["amp"] / f"{u['search']}.json") or {}
        held, sh = u["held"], u["search"]
        d = {"S": u["d"]["S"], "H": u["d"]["H"]}
        d["XO"] = (d["S"] if xo.get("fallback") else (xo.get("judge_shrunk") or {}).get(held)) if xo else None
        dr = {}
        if g.get("status") == "done":
            d["D"] = g["measure"][f"D|{sh}"][held]
            d["S_fresh"] = g["measure"]["S"][held]
            dr = {"S": g["raw"]["S"][held], **{a: g["raw"][f"{a}|{sh}"][held] for a in ("H", "XO", "D")}}
            for k in ("D",):                                  # a refused answer scores as S
                if d[k] is None or not math.isfinite(d[k]):
                    d[k] = d["S"]
                if dr[k] is None or not math.isfinite(dr[k]):
                    dr[k] = dr["S"]
        units.append({**{k: u[k] for k in ("slug", "band", "cls", "amp", "search", "held")}, "d": d, "d_raw": dr})
    return units


def row_filter(row, bt, unseen):
    from learn import arm_a_mega53 as A

    if row == "unseen_by_part_c":
        return lambda u: u["band"] in unseen
    return A.row_filter(row, "F", bt, {})


def contrast(units, a, b, key="d"):
    """a − b on the held half, per part then band-weighted (`arm_a_levers.effects`)."""
    from learn import arm_a_levers as L

    us = [{**u, "d": u[key]} for u in units if all(L.finite_pos(u[key].get(x)) for x in (a, b))]
    return L.effects(us, a, b) if us else None


def widening(units, a, b):
    """(raw − measure) of the log ratio a/b per direction, band-weighted with its interval; the
    band SD of each judge's contrast."""
    import statistics

    from learn import arm_a_levers as L
    from learn import song_readout as R

    def f(u):
        m, r = u["d"], u["d_raw"]
        if not all(L.finite_pos(z.get(x)) for z in (m, r) for x in (a, b)):
            return None
        return math.log(r[a] / r[b]) - math.log(m[a] / m[b])

    out = {"raw_minus_measure": R.bw(R.part_rows(units, f))}
    for key in ("d", "d_raw"):
        rows = R.part_rows([{**u, "d": u[key]} for u in units], R.log_vs(a, b))
        by = {}
        for band, _, v in rows:
            by.setdefault(band, []).append(v)
        means = [statistics.fmean(v) for v in by.values()]
        out[f"band_sd_{key}"] = statistics.stdev(means) if len(means) > 1 else None
    return out


def median(xs):
    import statistics

    xs = [x for x in xs if x is not None and math.isfinite(x)]
    return statistics.median(xs) if xs else None


def ka_summary(rows):
    """Per section (both halves): the truth's and S's distances under each judge; band-weighted
    log(truth / S) under each (distances floored at known_answer.D_FLOOR, as B1)."""
    from learn import known_answer as KAM
    from learn import song_readout as R

    out = {"sections": len(rows)}
    for j in ("raw", "measure"):
        vals = []
        for r in rows:
            for h in ("A", "B"):
                t, s = r[j]["truth"][h], r[j]["S"][h]
                vals.append((KAM.SONGS[r["song"]]["band"], math.log(max(t, KAM.D_FLOOR) / max(s, KAM.D_FLOOR))))
        out[j] = {"truth_median": median([r[j]["truth"][h] for r in rows for h in "AB"]),
                  "S_median": median([r[j]["S"][h] for r in rows for h in "AB"]),
                  "truth_over_S_median": median([r[j]["truth"][h] / r[j]["S"][h] for r in rows for h in "AB"]),
                  "log_truth_minus_S": R.bw_stats(vals)}
    out["stored_vs_fresh_measure_truth_max_dev"] = max(
        abs(math.log(r["measure"]["truth"][h] / r["stored"]["measure_truth"][h])) for r in rows for h in "AB")
    out["stored_vs_fresh_raw_S_max_dev"] = max(
        abs(math.log(r["raw"]["S"][h] / r["stored"]["raw_S"][h])) for r in rows for h in "AB")
    return out


def fmt(s):
    if not s or s.get("band_weighted_mean") is None:
        return "n/a"
    lo, hi = s.get("lo90"), s.get("hi90")
    return (f"{s['band_weighted_mean']:+.3f}" + ("" if lo is None else f" [{lo:+.3f}, {hi:+.3f}]")
            + f" ({s['bands']} bands, {s.get('bands_negative', '?')} better)")


def cmd_report(_args):
    from learn import local_objective_1c as C

    pred = _load(OUT / "predictions.json")
    units = build_units()
    done = [u for u in units if "D" in u["d"]]
    bt = C.load_bleed_table()
    unseen = set(pred["unseen_by_part_c"])
    rep = {"directions": len(units), "done": len(done), "renders": spent(), "expected": expected_renders(),
           "repeat_dev_max": max((_load(p) or {}).get("repeat_dev", 0) for p in (OUT / "groups").glob("*.json")),
           "test1": {}, "test2": {}, "medians": {}}
    for a, b in CONTRASTS:
        rep["test1"][f"{a}-{b}"] = {r: (contrast([u for u in done if row_filter(r, bt, unseen)(u)], a, b) or {}).get("all")
                                    for r in ROWS}
    for a, b in CONTRASTS:
        rep["test2"][f"{a}-{b}"] = {"measure": (contrast(done, a, b) or {}).get("all"),
                                    "raw": (contrast(done, a, b, "d_raw") or {}).get("all"), **widening(done, a, b)}
    for key in ("d", "d_raw"):
        rep["medians"][key] = {a: median([u[key].get(a) for u in done]) for a in ARMS_RAW}
    rep["per_amp_D_minus_S"] = (contrast(done, "D", "S") or {}).get("per_amp")
    rep["per_class_D_minus_S"] = (contrast(done, "D", "S") or {}).get("per_class")
    ka = [r for r in (_load(p) for p in sorted((OUT / "groups" / "ka").glob("*.json"))) if r and r.get("status") == "done"]
    rep["known_answer"] = ka_summary(ka) if ka else None
    rep["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save(OUT / "report.json", rep)
    print(f"{rep['done']}/{rep['directions']} directions; renders {rep['renders']} (expected {rep['expected']}); "
          f"repeat max {rep['repeat_dev_max']:.2e}")
    for k, v in rep["test1"].items():
        print(f"  {k:6s}", "  ".join(f"{r}: {fmt(v[r])}" for r in ROWS))
    for k, v in rep["test2"].items():
        print(f"  {k:6s} measure {fmt(v['measure'])}  raw {fmt(v['raw'])}  raw-measure {fmt(v['raw_minus_measure'])}"
              f"  band SD {v['band_sd_d']:.3f} -> {v['band_sd_d_raw']:.3f}")
    print("  medians", rep["medians"])
    if rep["known_answer"]:
        print("  known answer", json.dumps(rep["known_answer"], indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("parity", "predict", "render", "report"))
    ap.add_argument("--shard", type=lambda s: tuple(int(x) for x in s.split("/")), default=(0, 1))
    a = ap.parse_args(argv)
    {"parity": cmd_parity, "predict": cmd_predict, "render": cmd_render, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    main()
