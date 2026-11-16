"""Step 2, the preset ladder (`docs/preset-ladder-plan.md`; ledger `preset-ladder`): where between the guitar alone and the
product's stem is the preset lost? C3r's held-out real units (480 parts on 400 units) are each read by their fold's R-all
model from a ladder of inputs, every answer rendered through the unit's own DI and judged on the held half (J0), beside
S, the label and two constants: Cen, the training labels' centre, and Aconst, the model's own mean answer. Each unit
gets one lender, a D_CC example from another session that lends it other guitars, a backing, a loudness and a mastering
draw; the unit's amp track is placed in that session's stereo mix at a declared exposure. Staged, cheapest first, each
stage declared in the ledger before it runs:

    # stage 0 (zero renders)
    .venv/bin/python -m learn.preset_ladder lends                              # each unit's lender
    $TORCH_PY -m learn.preset_ladder check0                                    # controls: answers reproduce, fold bans
    $TORCH_PY -m learn.preset_ladder centres                                   # Cen, Aconst (+ all-labels centres.json)
    .venv/bin/python -m learn.preset_ladder build --rows clean-kind            # the clean track's features
    $TORCH_PY -m learn.preset_ladder predict --rows clean-kind,xl-v0           # their answers
    .venv/bin/python -m learn.preset_ladder stage0                             # the preview and the knob-space reads
    # stage 1 (renders)
    .venv/bin/python -m learn.preset_ladder check1                             # controls: S0's items, v0 rebuilt
    .venv/bin/python -m learn.preset_ladder build --rows mix@-3                # mix@-3, full@-3, clean@-3
    $TORCH_PY -m learn.preset_ladder predict --rows mix@-3
    .venv/bin/python -m learn.preset_ladder replay                             # control: 30 stored answers re-rendered
    .venv/bin/python -m learn.preset_ladder render --rows cen,aconst,clean-kind,mix@-3 --shard 0/3
    .venv/bin/python -m learn.preset_ladder report --stage 1
    # stage 2 (separations, then renders), declared before it runs
    ~/ndsp-presets/tools/msst-venv/bin/python -m learn.preset_ladder sep --rows xl@-3,xlnoG@-3 --device mps

The pure parts (the lender pool and draw, the layout, the gains, the stereo assembly, the centres, the subset, the rows)
are unit-tested in tests/test_preset_ladder.py.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time

LEDGER_ID = "preset-ladder"
PLAN = "docs/preset-ladder-plan.md"
OUT = "ladder"
PHASES = {0: "phase_l0", 1: "phase_l1", 2: "phase_l2", 3: "phase_l3"}
SEED = 20261161                       # the lenders, the layouts and the backing pans, each seeded by its unit
SUBSET_SEED = 20261162                # stage 3's subset
REPLAY_SEED = 20261163                # the replay control's sample
MAIN_EXPOSURE = "-3"                  # the target 3 dB under everything else in the mix's mid (T0x's product exposure)
EXPOSURES = ("drawn", "-3", "0")
HEAVY_BANDS = frozenset({"Ale Lak", "Storm Of Particles"})   # D_CC keeps their non-high-gain sections; read beside
TARGET_PAN = 0.15                     # S0's centred stratum: the target within +-0.15
OTHERS_PAN = (0.6, 1.0)               # every other guitar on one seeded side, +-0.6 to +-1.0
OTHERS_FLOOR_LUFS = -50.0             # a lender's other guitars quieter than this are silence (`trusted_data`'s floor)
REPLAY_N = 30
RATIO_EDGES = (-12.0, -6.0)           # stage 0's bins of the guitar-to-backing ratio (the planner's preview)
SETS = ("bks", "goat", "cap1", "n12", "panel")
SUBSET_GOAT_PER_FOLD = 6              # stage 3's subset: GOAT and cap1 units per fold and class
SUBSET_CAP1_PER_CREATOR = 3
KNOB_GROUPS = {                       # reads_v3's three groups, then the EQ and the drive pedals' continuous knobs
    "drive": ("inputGain", "pr12Volume", "sw50rVolume", "sw50rLevel", "ac20Volume", "ac20Power"),
    "tone": ("pr12Treble", "pr12Bass", "sw50rTreble", "sw50rMid", "sw50rBass", "ac20Cut"),
    "cab": ("leftCabPosition", "rightCabPosition", "leftCabDistance", "rightCabDistance", "rightCabMicLevel")}


def ladder_dir():
    from learn import pipeline_fix as P

    return P.out_dir() / OUT


def ledger_entry():
    from learn import pipeline_fix as P

    d = json.loads((P.REPO / "docs" / "dev-test-ledger.json").read_text())
    return next((t for t in d["tests"] if t["test_id"] == LEDGER_ID), None)


def require(stage):
    """Real runs refuse unless the ledger's `preset-ladder` entry declares the stage's phase."""
    key = PHASES[stage]
    e = ledger_entry()
    if not e or key not in e:
        raise SystemExit(f"the ledger's {LEDGER_ID} entry has no {key}: declare it before running")
    return e


# --- the rows (pure) -------------------------------------------------------------------------------------------------------

def exposure_value(tag):
    """An exposure tag -> the target-to-rest ratio in dB on the mix's mid, or None for the lender's own drawn ratio."""
    if tag not in EXPOSURES:
        raise SystemExit(f"exposure {tag!r}: one of {EXPOSURES}")
    return None if tag == "drawn" else float(tag)


def row_info(name):
    """A row's stage, kind and input style. kind: "stored" (C3r's own answers and scores), "constant" (one answer a
    part), "input" (an answer a half from features). style: "train" (the signal at its own level, `half_features`, as the
    model's training inputs) or "product" (the stem brought by the gain that takes its own mix to -12.25 LUFS)."""
    if name == "mix-drawn":
        return {"stage": 0, "kind": "stored", "style": "train"}
    if name in ("cen", "aconst"):
        return {"stage": 1, "kind": "constant", "style": None}
    if name == "clean-kind":
        return {"stage": 1, "kind": "input", "style": "train"}
    if name == "xl-v0":
        return {"stage": 2, "kind": "input", "style": "product"}
    if "@" in name:
        what, tag = name.split("@", 1)
        exposure_value(tag)
        main = tag == MAIN_EXPOSURE
        if what == "mix":
            return {"stage": 1 if main else 3, "kind": "input", "style": "train", "exposure": tag}
        if what == "full":                 # built beside mix@E, rendered only when a stage names it
            return {"stage": 3, "kind": "input", "style": "train", "exposure": tag}
        if what == "clean":
            return {"stage": 2 if main else 3, "kind": "input", "style": "product", "exposure": tag}
        if what in ("xl", "xlnoG"):
            return {"stage": 2 if main else 3, "kind": "input", "style": "product", "exposure": tag, "sep": True}
        if what == "xlmdxc":
            return {"stage": 3, "kind": "input", "style": "product", "exposure": tag, "sep": True}
    raise SystemExit(f"unknown row {name!r}")


def parse_rows(s):
    rows = [r for r in s.split(",") if r]
    for r in rows:
        row_info(r)
    return rows


# --- the lenders (pure) ----------------------------------------------------------------------------------------------------

def session_of_di(di):
    """'set/Session_Full/file.wav' -> 'set/Session_Full' (a DI file's session; a GOAT item or a panel DI gives its
    own prefix, which no D_CC session shares)."""
    return di.rsplit("/", 1)[0]


def lender_pool(cands, floor=OTHERS_FLOOR_LUFS):
    """The lender pool: {cls: {section: [example ids]}} of the candidates whose other guitars (the `others` render and
    the session's other-guitar amp tracks) are not silence. cands: [{i, cls, band, section, session, others_lufs}],
    already restricted to D_CC's recipe split (no NS song, no runaway or doubled example) and to bands other than BKS."""
    out = {}
    for c in cands:
        if c["band"] == "BKS":
            raise SystemExit(f"{c['i']}: a BKS lender (BKS's DIs are real training rows of every fold model)")
        if c["others_lufs"] is None or not math.isfinite(c["others_lufs"]) or c["others_lufs"] < floor:
            continue
        out.setdefault(c["cls"], {}).setdefault(c["section"], []).append(c["i"])
    return {k: {s: sorted(v) for s, v in sorted(d.items())} for k, d in sorted(out.items())}


def draw_lender(unit, cls, pool, section_session, own_session, seed=SEED):
    """A unit's lender: a section drawn uniformly among its class's pool sections from any session but the unit's
    own DI's, then an example of that section, both seeded by the unit. -> (section, example id)."""
    rng = random.Random(f"{seed}|ladder-lend|{unit}")
    secs = [s for s in sorted(pool.get(cls, {})) if section_session[s] != own_session]
    if not secs:
        raise SystemExit(f"{unit}: no lender section of class {cls}")
    s = rng.choice(secs)
    return s, rng.choice(pool[cls][s])


def draw_layout(unit, seed=SEED):
    """S0's centred stratum, seeded by the unit: the target within +-TARGET_PAN, every other guitar on one side at
    OTHERS_PAN. -> {"target": [p], "others": q}."""
    rng = random.Random(f"{seed}|ladder-layout|{unit}")
    t = rng.uniform(-TARGET_PAN, TARGET_PAN)
    side = rng.choice((-1, 1))
    return {"target": [t], "others": side * rng.uniform(*OTHERS_PAN)}


def backing_rng(unit, seed=SEED):
    """The backing tracks' pans (`sep_s0.backing_pan`, one draw a mono track in order), seeded by the unit."""
    return random.Random(f"{seed}|ladder-backing|{unit}")


def ladder_gains(lg, lb, draw, tag):
    """The mix's gains (`trusted_data.mix_gains`) for exposure `tag` on loudness values measured on the mid: the target
    `lg`, everything else `lb`; the lender's drawn ratio for "drawn", else the declared one; the lender's drawn mix
    loudness either way. -> (gb, ga) dB."""
    from learn import fx_t1x as T1X
    from learn import trusted_data as T

    r = exposure_value(tag)
    d = draw if r is None else T1X.with_ratio({"draw": draw}, r)["draw"]
    return T.mix_gains(lg, lb, d)


# --- the stereo mix (numpy) ------------------------------------------------------------------------------------------------

def place(y, p):
    """A mono source at pan p by the constant-power law, unfolded so that a centred copy's (L + R) / 2 is the source
    itself (`sep_s0`'s kt). -> (L, R)."""
    from learn import sep_s0 as S0

    kt = 1 / S0.pan(0.0)[0]
    gl, gr = S0.pan(p)
    return gl * y * kt, gr * y * kt


def assemble(y, others, tracks, guitar_amps, layout, rng, n):
    """S0's stereo build before its gains (`sep_s0.cmd_build`), with the other guitars kept apart from the stems. y: the
    target; others: the `others` render; tracks: [(name, [n, 2] audio, channels)] of the backing tracks in order;
    guitar_amps: the names among them that are other guitars (they sit with the others); rng: the backing pans' draw.
    -> {"t": (L, R), "o": (L, R) the others render, "a": (L, R) other-guitar amp tracks, "s": (L, R) the stems,
    "pans": {track: pan or "stereo"}}."""
    import numpy as np

    from learn import sep_s0 as S0
    from learn import trusted_data as T

    tL, tR = np.zeros(n), np.zeros(n)
    for p in layout["target"]:                     # one copy here (the centred stratum)
        a, b = place(np.asarray(y, np.float64)[:n], p)
        tL, tR = tL + a, tR + b
    oL, oR = place(np.asarray(others, np.float64)[:n], layout["others"])
    kb = T.pan_fold(0.0) / S0.pan(0.0)[0]          # a mono backing track centred folds as the recipe's (= 1)
    aL, aR, sL, sR, pans = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n), {}
    for name, x, ch in tracks:
        if ch == 1:
            pp = layout["others"] if name in guitar_amps else S0.backing_pan(name, rng)
            gl, gr = S0.pan(pp)
            l, r = x[:n, 0] * gl * kb, x[:n, 0] * gr * kb
            pans[name] = round(pp, 3)
        else:
            l, r = x[:n, 0], x[:n, 1]
            pans[name] = "stereo"
        if name in guitar_amps:
            aL, aR = aL + l, aR + r
        else:
            sL, sR = sL + l, sR + r
    return {"t": (tL, tR), "o": (oL, oR), "a": (aL, aR), "s": (sL, sR), "pans": pans}


def mid(lr):
    return (lr[0] + lr[1]) / 2


def mixdown(parts, gb, ga, with_others=True):
    """L and R of the mix at the gains (dB): (target + backing x gb) x ga, the backing holding the other guitars (the
    `others` render and the amp tracks) only `with_others`. -> {"L", "R", "target", "guitars"} (the last two are the
    target and the other guitars as they sit in the mid)."""
    g_b, g_a = 10 ** (gb / 20), 10 ** (ga / 20)
    (tL, tR), (oL, oR), (aL, aR), (sL, sR) = parts["t"], parts["o"], parts["a"], parts["s"]
    k = 1.0 if with_others else 0.0
    L = (tL + ((oL + aL) * k + sL) * g_b) * g_a
    R = (tR + ((oR + aR) * k + sR) * g_b) * g_a
    return {"L": L, "R": R, "target": (tL + tR) / 2 * g_a, "guitars": ((oL + aL) + (oR + aR)) / 2 * g_b * g_a * k}


def master(m, mastered, mrng, sr):
    """S0's mastering: a linked compressor on the mid, its gain and make-up on both channels and on the references,
    then each channel clipped at -1 dBFS. m: `mixdown`'s dict, changed copy returned."""
    import numpy as np

    from learn import sep_s0 as S0
    from learn import song_aug as SA

    if not mastered:
        return dict(m)
    md = (m["L"] + m["R"]) / 2
    g, mk = S0.linked_gain(md, mrng, sr)
    gm = 10 ** ((float(SA.lufs(md)) + mk - float(SA.lufs(md * g))) / 20)
    out = {k: v * g * gm for k, v in m.items()}
    peak = 10 ** (-1 / 20)
    out["L"], out["R"] = np.clip(out["L"], -peak, peak), np.clip(out["R"], -peak, peak)
    return out


# --- the constants (pure on encoded labels and answers) --------------------------------------------------------------------

def centre_of(rows, n_cont, n_sw, n_cat, s_mics=None):
    """The labels' centre, head by head: rows [(c, cm, s, sm, k, km)] (a record's encoded label and its training mask, one
    row per showing in an epoch). Continuous heads the mean of the masked values; switches the share on (the answer is
    on above 0.5, so the majority, a tie off); mics the most common masked index, a tie to S's (`s_mics`) when it is
    among the tied, else the lowest. A head no row labels stays None (S's value). -> (cont, sw_p, mics)."""
    from collections import Counter

    cont, swp, mics = [], [], []
    for j in range(n_cont):
        v = [r[0][j] for r in rows if r[1][j] > 0]
        cont.append(sum(v) / len(v) if v else float("nan"))
    for j in range(n_sw):
        v = [r[2][j] for r in rows if r[3][j] > 0]
        swp.append(sum(1.0 for x in v if x > 0.5) / len(v) if v else None)
    for j in range(n_cat):
        v = Counter(int(r[4][j]) for r in rows if r[5][j] > 0)
        if not v:
            mics.append(None)
            continue
        top = max(v.values())
        tied = sorted(m for m, c in v.items() if c == top)
        s = None if s_mics is None else s_mics[j]
        mics.append(s if s in tied else tied[0])
    return cont, swp, mics


def answers_centre(outs, n_cont, n_sw, n_cat, s_mics=None):
    """The model's own constant from its readouts on its training inputs: outs [(a2, sw_p, mics)] (one per showing and
    half). Continuous the mean answer; switches the share answered on (a tie off); mics the most common answer, a tie
    as `centre_of`'s. -> (cont, sw_p, mics)."""
    rows = [(a2, [1.0] * n_cont, [1.0 if p > 0.5 else 0.0 for p in sw], [1.0] * n_sw, mic, [1.0] * n_cat)
            for a2, sw, mic in outs]
    return centre_of(rows, n_cont, n_sw, n_cat, s_mics)


def showing_counts(recs):
    """{(unit, amp): showings in one epoch} of a source's records cycled as the training cycles them."""
    out = {}
    for r in recs:
        k = (r["unit"], r["amp"])
        out[k] = out.get(k, 0) + 1
    return out


# --- the subset (pure) -----------------------------------------------------------------------------------------------------

def subset_draw(units, seed=SUBSET_SEED):
    """Stage 3's subset, seeded: every BKS and panel unit; per fold SUBSET_GOAT_PER_FOLD clean and as many crunch GOAT
    units, one a GOAT item; per fold as many cap1 units of each class, at most SUBSET_CAP1_PER_CREATOR a creator.
    units: [{set, unit, fold, cls, item, creator}] one per unit. -> sorted unit names."""
    rng = random.Random(seed)
    out = {u["unit"] for u in units if u["set"] in ("bks", "panel")}
    n = SUBSET_GOAT_PER_FOLD
    for f in sorted({u["fold"] for u in units}):
        g = sorted((u for u in units if u["set"] == "goat" and u["fold"] == f), key=lambda u: u["unit"])
        rng.shuffle(g)
        used, got = set(), {"clean": 0, "crunch": 0}
        for u in g:
            if got.get(u["cls"], n) < n and u["item"] not in used:
                out.add(u["unit"])
                used.add(u["item"])
                got[u["cls"]] += 1
        c = sorted((u for u in units if u["set"] == "cap1" and u["fold"] == f), key=lambda u: u["unit"])
        rng.shuffle(c)
        per, got = {}, {"clean": 0, "crunch": 0}
        for u in c:
            if got.get(u["cls"], n) < n and per.get(u["creator"], 0) < SUBSET_CAP1_PER_CREATOR:
                out.add(u["unit"])
                per[u["creator"]] = per.get(u["creator"], 0) + 1
                got[u["cls"]] += 1
    return sorted(out)


# --- the reads (pure) ------------------------------------------------------------------------------------------------------

def ratio_bin(r, edges=RATIO_EDGES):
    if r is None:
        return None
    if r < edges[0]:
        return f"under {edges[0]:+.0f} dB"
    if r < edges[1]:
        return f"{edges[0]:+.0f} to {edges[1]:+.0f} dB"
    return f"{edges[1]:+.0f} dB and over"


def gap_share(row_vals, label_vals):
    """The share of the constant-to-label gap a row closes, on the directions where both exist: mean ln(row / Cen) over
    mean ln(label / Cen). row_vals, label_vals: {direction: value}. -> (share, directions) or (None, n)."""
    both = sorted(set(row_vals) & set(label_vals))
    if not both:
        return None, 0
    lab = sum(label_vals[k] for k in both) / len(both)
    return (None if lab == 0 else sum(row_vals[k] for k in both) / len(both) / lab), len(both)


def slope(xs, ys):
    """Least-squares slope of ys on xs (descriptive), or None."""
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    return None if sxx == 0 else sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx


def within_cell(values):
    """values: [(cell, unit, x)] -> {unit: x less its cell's mean} (cells with one value dropped)."""
    by = {}
    for c, u, x in values:
        by.setdefault(c, []).append((u, x))
    out = {}
    for xs in by.values():
        if len(xs) < 2:
            continue
        m = sum(x for _, x in xs) / len(xs)
        for u, x in xs:
            out[u] = x - m
    return out


def corr(a, b):
    n = len(a)
    if n < 3:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    va, vb = sum((x - ma) ** 2 for x in a), sum((y - mb) ** 2 for y in b)
    return None if va == 0 or vb == 0 else sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


# --- I/O helpers -----------------------------------------------------------------------------------------------------------

def fname(key):
    return key.replace("/", "__").replace(" ", "_")


def feat_path(row, ru):
    return ladder_dir() / "feats" / row / f"{ru['set']}__{fname(ru['unit'])}.npz"


def build_path(tag, ru):
    return ladder_dir() / "builds" / tag / f"{ru['set']}__{fname(ru['unit'])}.json"


def answers_path(row):
    return ladder_dir() / "answers" / f"{row}.json"


def judge_path(row, ru):
    return ladder_dir() / "judge" / row / ru["set"] / f"{fname(ru['unit'] + '|' + ru['amp'])}.json"


def units_once(read_units):
    """C3r's read parts -> one per unit (a BKS unit's three amps share its audio and its lender)."""
    seen, out = set(), []
    for ru in read_units:
        if ru["unit"] not in seen:
            seen.add(ru["unit"])
            out.append(ru)
    return out


def fold_models(st, which=range(4)):
    """{fold: (nets, model sha256s, run records)}: C3r-all's FT_k pair per fold (both seeds, the read checkpoint), each
    run checked as `cmd_predict` checks it; fold None: the all-labels pair (adopted-model.json's)."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P

    base = R.base_of("all", st)
    out = {}
    for k in which:
        nm = base if k is None else P.ft_name(k, base=base)
        nets, recs = zip(*(P.load_run(nm, sd, "best") for sd in P.SEEDS))
        for r_ in recs:
            R.run_info_check(r_, st)
            if r_.get("inner") or r_["models"]["best"] != r_["models"]["final"]:
                raise SystemExit(f"{nm}-{r_['seed']}: not a read checkpoint")
        out[k] = (list(nets), [r_["model_sha256"]["best"] for r_ in recs], list(recs))
    return out


def answer_of(nets, x, c, amp, S, hold):
    """One input's answer, exactly as `full_controls_c3r.cmd_predict` makes it. -> settings {(module, key): stored}."""
    from learn import full_space as F
    from learn import pipeline_fix as P

    r = F.readout([o[0] for o in F.run_nets(nets, [x], [c])])
    stg = F.answer_settings(amp, S, r["a2"], r["sw_p"], r["mics"])
    return P.hold_outside_space(stg, S, amp) if hold is None else P.hold_outside_space(stg, S, amp, hold)


def save_answers(row, answers, extra):
    from learn import pipeline_fix as P

    P.save(answers_path(row), dict({"plan": PLAN, "ledger": LEDGER_ID, "row": row, "answers": answers}, **extra,
                                   time=time.strftime("%Y-%m-%d %H:%M:%S")))


# --- the lenders (zero renders) --------------------------------------------------------------------------------------------

def cmd_lends(_args):
    """Each unit's lender (zero renders): D_CC's recipe split (W's training and FS examples: no NS song, no runaway or
    doubled example), bands other than BKS, whose other guitars measure above the floor; a section drawn uniformly among
    the unit's class's sections from any session but its own DI's, then an example of it. -> ladder/lends.json."""
    import numpy as np

    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_aug as SA
    from learn import trusted_data as T

    require(0)
    e = P.require("phase_dfix")
    croot, kept, rend, sp, _ = P.recipe_inputs(pin=e.get("phase_3_doubles"))
    stems = T.Stems(CB.ctx_for(argparse.Namespace(out=None, smoke=False)))
    cands, t0 = [], time.time()
    ids = sorted(set(sp["train"]) | set(sp["fs"]))
    n = int(round(PS.SEC_S * PS.SR))
    for m, i in enumerate(ids):
        x = kept[i]
        if x["band"] == "BKS" or P.session_of(x["section"]) in P.NS_SESSIONS:
            continue
        rw = rend[i]
        o = np.zeros(n)
        if rw.get("others_file") and x.get("others"):
            o = np.asarray(G.read_flac(T.flac_path(croot, CB.STAGE, i, "others"), rw["others_file"]["scale"],
                                       rw["others_file"]["sha256"]), np.float64)[:n]
        amps = [a["track"] for a in x.get("amp_tracks") or []]
        if amps:
            o = o + np.asarray(stems.get(x["section"], amps), np.float64)[:n]
        lv = float(SA.lufs(o)) if np.any(o) else None
        cands.append({"i": i, "cls": x["cls"], "band": x["band"], "section": x["section"],
                      "session": P.session_of(x["section"]), "others_lufs": lv, "n_others": len(x.get("others") or []),
                      "n_amp_tracks": len(amps)})
        if m % 200 == 0:
            print(f"lends: {m + 1}/{len(ids)} candidates measured, {time.time() - t0:.0f} s", flush=True)
    pool = lender_pool(cands)
    sess = {c["section"]: c["session"] for c in cands}
    by_i = {c["i"]: c for c in cands}
    st = R.state()
    out = {}
    for ru in units_once(R.read_units(st)):
        prt = ru["prt"]
        s, i = draw_lender(ru["unit"], prt["cls"], pool, sess, session_of_di(prt["di"]))
        c = by_i[i]
        out[ru["unit"]] = {"set": ru["set"], "cls": prt["cls"], "lend": i, "section": s, "band": c["band"],
                           "others_lufs": c["others_lufs"], "n_others": c["n_others"], "n_amp_tracks": c["n_amp_tracks"],
                           "layout": draw_layout(ru["unit"])}
    counts, by_band = {}, {}
    for v in out.values():
        k = f"{v['cls']}|{v['band']}"
        counts[k] = counts.get(k, 0) + 1
    for cls, secs in pool.items():
        for sec, xs in secs.items():
            k = f"{cls}|{by_i[xs[0]]['band']}"
            by_band.setdefault(k, {"sections": 0, "examples": 0})
            by_band[k]["sections"] += 1
            by_band[k]["examples"] += len(xs)
    P.save(ladder_dir() / "lends.json", {
        "plan": PLAN, "ledger": f"{LEDGER_ID} {PHASES[0]}", "rule": cmd_lends.__doc__, "seed": SEED,
        "candidates": len(cands), "pool": {k: {"sections": len(v), "examples": sum(len(x) for x in v.values())}
                                           for k, v in pool.items()},
        "pool_by_band": dict(sorted(by_band.items())),
        "silent_out": sum(1 for c in cands if c["others_lufs"] is None or c["others_lufs"] < OTHERS_FLOOR_LUFS),
        "lent_by": dict(sorted(counts.items())), "units": out, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"LENDS DONE: {len(out)} units; {len(cands)} candidates; pool {json.dumps({k: len(v) for k, v in pool.items()})}"
          f"; lent {json.dumps(dict(sorted(counts.items())))}")


def lends():
    p = ladder_dir() / "lends.json"
    if not p.exists():
        raise SystemExit(f"{p}: run `lends` first")
    return json.loads(p.read_text())


# --- stage 0's controls (zero renders) -------------------------------------------------------------------------------------

def cmd_check0(_args):
    """Stage 0's controls (CPU): the ladder's answer code reproduces C3r's stored R-all answers from the stored variant-0
    inputs (equal sha256); the fold bans re-derived (each read unit's fold model trains on no unit of its fold or sharing
    its DI or creator, the run records' own counts agreeing); the stored scores reproduce C3r's report rows.
    -> ladder/controls/check0.json; a failure stops stage 0."""
    from learn import direct_stems as DS
    from learn import full_controls_c3r as R
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    require(0)
    st = R.state()
    stored = json.loads(R.answers_path("all").read_text())
    if stored["c3r_sha256"] != st["sha256"]:
        raise SystemExit("C3r's stored answers were made on another state")
    models = fold_models(st)
    if {str(k): v[1] for k, v in models.items()} != stored["models"]:
        raise SystemExit("the fold models differ from those C3r's answers name")
    ms, hold, out = P.A_menu_S(), R.answer_hold(st), {}
    units = R.read_units(st)
    for ru in units:
        nets = models[ru["fold"]][0]
        sel, S = ms[ru["amp"]][ru["prt"]["cls"]]
        backed = P.dfix_backed(ru["unit"])
        for h in ("A", "B"):
            s8, ls = backed[h]
            x, c = DS.model_input(s8, s8, ls, ls, h, ru["amp"], ru["prt"]["cls"], "Dstem")
            out.setdefault(ru["set"], {}).setdefault(f"{ru['unit']}|{ru['amp']}", {})[h] = {
                "select": sel, "settings": LO.sdict(answer_of(nets, x, c, ru["amp"], S, hold))}
    same = P.answers_sha(out) == P.answers_sha(stored["answers"])
    bans = fold_bans(st, units, models)
    rows = stored_rows_check(st, units)
    rec = {"answers_reproduce": same, "answers_sha256": P.answers_sha(out), "bans": bans, "report_rows": rows,
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(ladder_dir() / "controls" / "check0.json", rec)
    ok = same and not bans["problems"] and rows["max_abs_diff"] < 1e-9
    print(f"CHECK0 {'OK' if ok else 'FAILED'}: answers reproduce {same}; ban problems {len(bans['problems'])}; "
          f"report rows max diff {rows['max_abs_diff']:.2e}")
    if not ok:
        raise SystemExit("a stage 0 control failed: stage 0 stops")


def fold_bans(st, units, models):
    """The fold bans, re-derived: per fold, `full_controls_c3r.split`'s training entries against the run records'
    stored counts (train units per set, records, showings) and held units; each read part's unit neither trains in its
    model nor shares an identity with a training unit. -> {"problems": [...], "folds": {...}}."""
    from learn import full_controls_c3r as R

    probs, folds = [], {}
    ent = {e["unit"]: e for e in st["entries"]}
    for k in range(R.FOLDS):
        tr, held, _ = R.split(st["entries"], k, False, "all")
        ids = set().union(*[e["ids"] for e in tr]) if tr else set()
        names = {e["unit"] for e in tr}
        _, _, info = R.rows_for("all", k, False, st)
        for r_ in models[k][2]:
            got = r_.get("c3r") or {}
            for f in ("train_units", "held_units", "train_records", "showings"):
                if got.get(f) != info.get(f):
                    probs.append(f"fold {k} seed {r_['seed']}: {f} {got.get(f)} against {info.get(f)}")
        folds[k] = {"train_units": info["train_units"], "held_units": info["held_units"]}
        for ru in units:
            if ru["fold"] != k:
                continue
            e = ent[ru["unit"]]
            if ru["unit"] in names:
                probs.append(f"{ru['unit']}: trains in its own fold's model")
            if e["ids"] & ids:
                probs.append(f"{ru['unit']}: shares {sorted(e['ids'] & ids)} with fold {k}'s training units")
    return {"problems": probs, "folds": folds}


def stored_rows_check(st, units):
    """The ladder's pairing reproduces C3r's report: R-all - S per set from the stored judge files. -> max |diff|."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P

    rep = json.loads((R.c3r_dir() / "report.json").read_text())
    got = rows_for_pair(st, units, val_stored(st), val_s(st))
    diff = {}
    for s in SETS:
        main = [r[:3] for r in got[s] if not apart(r, units)]
        m = P.clustered(main)["mean"]
        want = rep["rows"]["R-all - S"][s]["mean"]
        diff[s] = None if m is None or want is None else abs(m - want)
    return {"diff": diff, "max_abs_diff": max(v for v in diff.values() if v is not None)}


# --- the values (zero renders) ---------------------------------------------------------------------------------------------

def val_stored(st):
    """R-all on its stored input (C3r's judge files, arm all): (ru, search, held) -> distance or None."""
    from learn import full_controls_c3r as R

    cache = {}

    def f(ru, sh, h):
        k = (ru["set"], ru["unit"], ru["amp"])
        if k not in cache:
            p = R.judge_path("all", ru)
            cache[k] = json.loads(p.read_text())["judge"] if p.exists() else None
        return R.half_value(cache[k], sh, h)
    return f


def val_s(st):
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P

    cache = {}

    def f(ru, sh, h):
        k = (ru["set"], ru["unit"], ru["amp"])
        if k not in cache:
            cache[k] = R.s_judges(st, ru)
        return R.half_value({P.ANY_HALF: cache[k]}, sh, h)
    return f


def label_judges(st):
    """{(unit, amp): (search half, {A, B})}: each C2 or C2r record's fresh label score (one direction a record)."""
    out = {}
    for d in (st["c2"], st["c2r"]):
        for r in d["records"]:
            o = d["outputs"].get(r["key"]) or {}
            j = ((o.get("fresh") or {}).get("label") or {}).get("judge")
            if j and o.get("search"):
                out[(r["unit"], r["amp"])] = (o["search"], j)
    return out


def val_label(st):
    from learn import full_controls_c3r as R

    lab = label_judges(st)

    def f(ru, sh, h):
        x = lab.get((ru["unit"], ru["amp"]))
        if x is None or x[0] != sh:
            return None
        return R.half_value({sh: x[1]}, sh, h)
    return f


def val_row(row):
    """A ladder row's renders (ladder/judge/<row>/), or C3r's stored ones for `mix-drawn`."""
    from learn import full_controls_c3r as R

    if row == "mix-drawn":
        return val_stored(None)
    cache = {}

    def f(ru, sh, h):
        k = (ru["set"], ru["unit"], ru["amp"])
        if k not in cache:
            p = judge_path(row, ru)
            cache[k] = json.loads(p.read_text())["judge"] if p.exists() else None
        return R.half_value(cache[k], sh, h)
    return f


def val_centre(tag):
    """5C's stored core centres (RcBG, RcGk on GOAT; RcBG, Rcs2 on BKS): their judge files, both halves of one render."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P

    cache = {}

    def f(ru, sh, h):
        k = (ru["set"], ru["unit"], ru["amp"])
        if k not in cache:
            d = {"goat": P.GOAT_DIR, "bks": P.REAL_DIR}.get(ru["set"])
            p = None if d is None else P.out_dir() / d / "judge" / tag / f"{(ru['unit'] + '|' + ru['amp']).replace('/', '__')}.json"
            cache[k] = json.loads(p.read_text())["judge"] if p is not None and p.exists() else None
        return R.half_value(cache[k], sh, h)
    return f


def rows_for_pair(st, units, fa, fb):
    """{set: [(cluster, unit|amp, ln(a / b), search half)]} on every direction both judge finite (C3r's pairing)."""
    out = {s: [] for s in SETS}
    for ru in units:
        for sh, h in (("A", "B"), ("B", "A")):
            a, b = fa(ru, sh, h), fb(ru, sh, h)
            if a is None or b is None:
                continue
            out[ru["set"]].append((ru["cluster"], ru["unit"] + "|" + ru["amp"], math.log(a / b), sh))
    return out


def apart(row, units, wd=None):
    """C3r's `_apart`: a new set's direction whose DI file is among W's plugin rows is read apart."""
    from learn import full_controls_c3r as R
    from learn import score_ear as SE

    if wd is None:
        wd = _W_DIS.setdefault("w", set(SE.w_dis()))
    return R._apart(row[:3], units, wd)


_W_DIS = {}


# --- the constants (CPU, zero renders) -------------------------------------------------------------------------------------

def training_records(st, k):
    """Model k's real training records, each as often as one epoch shows it: `full_controls_c3r.rows_for`'s sources,
    mixed and cycled exactly as the training does (k None: the all-labels model's). -> [{unit, amp, set}]."""
    from learn import full_controls_c3r as R

    tr, _, _ = R.split(st["entries"], k, False, "all")
    by = {}
    for e in tr:
        by.setdefault(e["set"], []).append(e["unit"])
    recs = R.records_of(st, by)
    out = []
    for name, v in recs.items():
        out += R.cycled_to(R.mixed(v, R.mix_seed("all", k, False, name)))
    return out


def classes(st):
    """{unit: class} over every set's units (a training record's class is its unit's)."""
    out = {}
    for s in SETS:
        out.update({u: p["cls"] for u, p in st["units"][s].items()})
    return out


def cmd_centres(_args):
    """Cen and Aconst for every read part (CPU, zero renders), and the all-labels versions (ladder/centres.json, for Steps
    1 and 3; never read on these units). Per fold k, amp and class, over model k's training records (each as often as an
    epoch shows it): Cen from their training labels under C3's training mask (`centre_of`); Aconst from model k's own
    readouts on their stored variant-0 inputs, both halves (`answers_centre`). Each written by `full_space.answer_settings`
    and C3r's answer hold (C3-cabS). -> ladder/answers/{cen,aconst}.json."""
    import numpy as np

    from learn import direct_stems as DS
    from learn import full_controls_c3 as C3
    from learn import full_controls_c3r as R
    from learn import full_space as F
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    require(0)
    st = R.state()
    ms, hold = P.A_menu_S(), R.answer_hold(st)
    keys_of, label_of = C3.keys_fn(st["sources"]), C3.label_fn(st["sources"])
    models = fold_models(st, which=list(range(R.FOLDS)) + [None])
    units = R.read_units(st)
    need = {(ru["fold"], ru["amp"], ru["prt"]["cls"]) for ru in units}
    need |= {(None, a, c) for a in P.AMPS3 for c in ("clean", "crunch")}
    cache, used = {}, {}

    def readouts(nets, unit, amp, cls):
        k_ = (id(nets), unit, amp)
        if k_ not in cache:
            backed = P.dfix_backed(unit)
            xs, cs = [], []
            for h in ("A", "B"):
                s8, ls = backed[h]
                x, c = DS.model_input(s8, s8, ls, ls, h, amp, cls, "Dstem")
                xs.append(x)
                cs.append(c)
            outs = F.run_nets(nets, xs, cs)
            cache[k_] = []
            for j in range(len(xs)):
                r = F.readout([o[j] for o in outs])
                cache[k_].append((list(map(float, r["a2"])), list(map(float, r["sw_p"])), list(r["mics"])))
        return cache[k_]

    consts, cls_of, probs = {}, classes(st), []
    ent = {e["unit"]: e for e in st["entries"]}
    for k in sorted({q[0] for q in need}, key=lambda v: (v is None, v)):
        recs = training_records(st, k)
        if k is not None:                          # no record of fold k or sharing an identity with a fold-k unit
            ban = set().union(*[e["ids"] for e in st["entries"] if e["fold"] == k])
            probs += [f"fold {k}: {r['unit']}" for r in recs if ent[r["unit"]]["fold"] == k or ent[r["unit"]]["ids"] & ban]
        nets = models[k][0]
        for amp in P.AMPS3:
            for cls in ("clean", "crunch"):
                if (k, amp, cls) not in need:
                    continue
                sel, S = ms[amp][cls]
                s_enc = F.encode(dict(S), amp)
                s_mics = [int(v) if m else None for v, m in zip(s_enc[4], s_enc[5])]
                mine = [r for r in recs if r["amp"] == amp and cls_of[r["unit"]] == cls]
                lab_rows = []
                for r in mine:
                    lab = label_of(r)
                    c, cm, s, sm, kk, km, _ = F.encode(LO.tdict(lab["settings"]), amp)
                    hc, hs, hk = C3.head_masks(keys_of(r["unit"], amp, S))
                    lab_rows.append((c, cm * hc, s, sm * hs, kk, km * hk))
                cen = centre_of(lab_rows, len(F.CONT), len(F.SW), len(F.CAT), s_mics)
                outs = [o for r in mine for o in readouts(nets, r["unit"], amp, cls)]
                acon = answers_centre(outs, len(F.CONT), len(F.SW), len(F.CAT), s_mics)
                for tag, (cont, swp, mics) in (("cen", cen), ("aconst", acon)):
                    stg = F.answer_settings(amp, S, np.array(cont, np.float64), swp, mics)
                    stg = P.hold_outside_space(stg, S, amp, hold) if hold is not None else P.hold_outside_space(stg, S, amp)
                    consts[(tag, k, amp, cls)] = {"select": sel, "settings": LO.sdict(stg)}
                used[f"{k}|{amp}|{cls}"] = {"showings": len(mine), "records": len({(r["unit"], r["amp"]) for r in mine})}
        print(f"centres: fold {k} done", flush=True)
    if probs:
        raise SystemExit(f"a constant would use a held unit's identity: {probs[:3]}")
    for tag in ("cen", "aconst"):
        ans = {}
        for ru in units:
            ans.setdefault(ru["set"], {})[f"{ru['unit']}|{ru['amp']}"] = {
                P.ANY_HALF: consts[(tag, ru["fold"], ru["amp"], ru["prt"]["cls"])]}
        save_answers(tag, ans, {"c3r_sha256": st["sha256"], "models": {str(k): v[1] for k, v in models.items()},
                                "records_used": used, "rule": cmd_centres.__doc__})
    P.save(ladder_dir() / "centres.json", {
        "plan": PLAN, "ledger": f"{LEDGER_ID} {PHASES[0]}", "about": (
            "The all-labels constants (every C3r training record, each as often as an epoch shows it; never read on the "
            "ladder's units): cen = the training labels' centre under C3's mask; aconst = the all-labels R-all pair's "
            "mean answer on those records' stored variant-0 inputs. Each per amp and class on that class's S, held as "
            "C3r's answers (C3-cabS). The output gain is S's (the loudness step sets it in the product)."),
        "hold": st["answer_tag"], "model_sha256": models[None][1], "c3r_sha256": st["sha256"],
        "centres": {tag: {amp: {cls: consts[(tag, None, amp, cls)] for cls in ("clean", "crunch")} for amp in P.AMPS3}
                    for tag in ("cen", "aconst")},
        "records_used": {k: v for k, v in used.items() if k.startswith("None|")},
        "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"CENTRES DONE: {len(units)} parts; all-labels centres in {ladder_dir() / 'centres.json'}")


# --- the inputs (zero renders) ---------------------------------------------------------------------------------------------

def save_feats(path, mels, lufs, **meta):
    import numpy as np

    from learn import direct_stems as DS

    DS._save_npz(path, sA=mels["A"], sB=mels["B"], lufs=np.array([lufs["A"], lufs["B"]], np.float32), **meta)


def load_feats(row, ru):
    """A row's stored input features -> {half: (uint8 mel, LUFS)} or None. `xl-v0` reads A2s's stems."""
    import numpy as np

    from learn import pipeline_fix as P

    if row == "mix-drawn":
        return P.dfix_backed(ru["unit"])
    if row == "xl-v0":
        p = P.out_dir() / "a2s" / "stems" / f"{ru['set']}__{ru['unit'].replace('/', '__')}.npz"
        if not p.exists():
            return None
        z = np.load(p)
        return {h: (z[f"s{h}"], float(z[f"lufs{h}"][0])) for h in ("A", "B")}
    p = feat_path(row, ru)
    if not p.exists():
        return None
    z = np.load(p)
    return {"A": (z["sA"], float(z["lufs"][0])), "B": (z["sB"], float(z["lufs"][1]))}


def model_lufs(st):
    """{fold: the training inputs' median loudness} of each fold pair (`pipeline_fix.model_input_lufs`, the clean
    branch's level, as D_fix's `-clean` read), from the run records alone."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P

    base = R.base_of("all", st)
    out = {}
    for k in range(R.FOLDS):
        rec = json.loads((P.out_dir() / "runs" / f"{P.ft_name(k, base=base)}-{P.SEEDS[0]}.json").read_text())
        out[k] = P.model_input_lufs(rec)
    return out


def lender_mix(ctx, croot, kept, rend, stems_cache, unit_audio, lend, tag, sr):
    """One unit's two mixes at exposure `tag` (zero renders): the unit's amp track levelled to the lender's target loudness
    (`pipeline_fix.dfix_level`) in the lender's stereo session (S0's centred layout, the unit's own seed), the ratio set
    on the mid against everything else; `full` with the other guitars, `noG` with the same gains and without them; each
    mastered by the lender's draw. -> ({"full": mixdown dict, "noG": ...}, record)."""
    import hashlib
    import pathlib

    import numpy as np

    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import pipeline_fix as P
    from learn import sep_s0 as S0
    from learn import song_aug as SA
    from learn import trusted_data as T

    i = lend["lend"]
    x, rw = kept[i], rend[i]
    y = np.asarray(G.read_flac(T.flac_path(croot, CB.STAGE, i, "target"), rw["target"]["scale"], rw["target"]["sha256"]),
                   np.float64)
    n = len(y)
    gtr, g_lvl = P.dfix_level(np.asarray(unit_audio, np.float64)[:n], float(SA.lufs(y)), SA.lufs)
    if len(gtr) != n:
        raise SystemExit(f"{lend['lend']}: the amp track has {len(gtr)} samples against the lender's {n}")
    oth = np.zeros(n)
    if rw.get("others_file") and x.get("others"):
        oth = np.asarray(G.read_flac(T.flac_path(croot, CB.STAGE, i, "others"), rw["others_file"]["scale"],
                                     rw["others_file"]["sha256"]), np.float64)[:n]
    voc = bool(x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"])
    tracks = T.backing_tracks(x, voc)
    sec = ctx.sections[x["section"]]
    sess = pathlib.Path(ctx.inv[sec["di"]]["session_dir"])
    key = (x["section"], tuple(tracks))
    if key not in stems_cache:
        stems_cache.clear()
        stems_cache[key] = [(t, *S0.load_track(sess / t, sec["start_s"], sr)) for t in tracks]
    guitar_amps = {a["track"] for a in x.get("amp_tracks") or []}
    parts = assemble(gtr, oth, stems_cache[key], guitar_amps, lend["layout"], backing_rng(lend["unit"]), n)
    t_mid = mid(parts["t"])
    rest = mid(parts["o"]) + mid(parts["a"]) + mid(parts["s"])
    lg, lb = float(SA.lufs(t_mid)), float(SA.lufs(rest))
    gb, ga = ladder_gains(lg, lb, x["draw"], tag)
    mastered = DS.master_draw(i)[0]
    if mastered != x["draw"]["mastered"]:
        raise SystemExit(f"{i}: the mastering draw changed")
    out = {}
    for name, with_o in (("full", True), ("noG", False)):
        out[name] = master(mixdown(parts, gb, ga, with_o), mastered, DS.master_draw(i)[1], sr)
    f, g = out["full"], out["noG"]
    fm, gm = (f["L"] + f["R"]) / 2, (g["L"] + g["R"]) / 2
    lu = lambda v: float(SA.lufs(v))                       # noqa: E731
    rec = {"unit": lend["unit"], "lend": i, "band": x["band"], "section": x["section"], "exposure": tag,
           "drawn_ratio_db": x["draw"]["ratio_db"], "gains_db": {"gb": gb, "ga": ga, "guitar_level": g_lvl},
           "mastered": mastered, "layout": lend["layout"], "pans": parts["pans"], "vocals": voc,
           "n_others": len(x.get("others") or []), "n_amp_tracks": len(guitar_amps),
           "full": {"target_to_rest_db": lu(f["target"]) - lu(fm - f["target"]),
                    "target_to_guitars_db": lu(f["target"]) - lu(f["guitars"]) if np.any(f["guitars"]) else None,
                    "mid_lufs": lu(fm), "mid_sha256": hashlib.sha256(np.asarray(fm, np.float32).tobytes()).hexdigest()},
           "noG": {"target_to_rest_db": lu(g["target"]) - lu(gm - g["target"]), "mid_lufs": lu(gm),
                   "mid_sha256": hashlib.sha256(np.asarray(gm, np.float32).tobytes()).hexdigest()}}
    return out, rec


def cmd_build(args):
    """Input features (CPU, zero renders). `clean-kind`: the unit's amp track alone at its fold models' training inputs'
    median loudness, both halves (`pipeline_fix.real_predict_5b2`'s clean branch). `mix@E` (with `full@E` and `clean@E`
    from the same build): the lender mixes (`lender_mix`): mix@E is noG's mid read as the training inputs are
    (`half_features`, no separator); full@E the same with the other guitars; clean@E the target as it sits in full's mid
    at the product's gain (a perfect separator). -> ladder/feats/<row>/, ladder/builds/<E>/<unit>.json."""
    import argparse as AP

    from learn import cc_build as CB
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import product_path as PP
    from learn import trusted_data as T

    rows = parse_rows(args.rows)
    for r in rows:                                 # the clean track's features are stage 0's (its answers feed the
        require(0 if r == "clean-kind" else row_info(r)["stage"])   # knob reads); a mix is its row's stage
    st = R.state()
    units = units_once(R.read_units(st))
    k, n = args.shard
    mine = [ru for j, ru in enumerate(units) if j % n == k]
    t0 = time.time()
    if "clean-kind" in rows:
        target = model_lufs(st)
        for ru in mine:
            p = feat_path("clean-kind", ru)
            if p.exists():
                continue
            prt = ru["prt"]
            ref = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
            g = DE.inference_gain_db(ref, target[ru["fold"]])
            mels, lu = {}, {}
            for h in ("A", "B"):
                mels[h], _, lu[h], _ = DS.step4_half(ref, ref, h, g)
            save_feats(p, mels, lu, gain_db=g, target_lufs=target[ru["fold"]])
        print(f"BUILD clean-kind: {len(mine)} units, {time.time() - t0:.0f} s", flush=True)
    tags = sorted({row_info(r)["exposure"] for r in rows if r.startswith("mix@")})
    if not tags:
        return
    if PS.free_gb() < T.DISK_GUARD_GB:
        raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
    e = P.require("phase_dfix")
    croot, kept, rend, _, _ = P.recipe_inputs(pin=e.get("phase_3_doubles"))
    ctx = CB.ctx_for(AP.Namespace(out=None, smoke=False))
    ld = lends()["units"]
    cache = {}
    order = sorted(mine, key=lambda ru: (ld[ru["unit"]]["section"], ru["unit"]))    # one session's stems loaded once
    for tag in tags:
        for m, ru in enumerate(order):
            bp = build_path(tag, ru)
            if bp.exists():
                continue
            prt = ru["prt"]
            lend = dict(ld[ru["unit"]], unit=ru["unit"])
            ref = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
            mixes, rec = lender_mix(ctx, croot, kept, rend, cache, ref, lend, tag, PS.SR)
            f, g = mixes["full"], mixes["noG"]
            fm, gm = (f["L"] + f["R"]) / 2, (g["L"] + g["R"]) / 2
            for row, sig in ((f"mix@{tag}", gm), (f"full@{tag}", fm)):
                mels, lu, floor = DS.half_features(sig)
                save_feats(feat_path(row, ru), mels, lu, floor=floor)
            gp = DE.inference_gain_db(fm, PP.MIX_LEVEL)
            mels, lu = {}, {}
            for h in ("A", "B"):
                mels[h], _, lu[h], _ = DS.step4_half(f["target"], fm, h, gp)
            save_feats(feat_path(f"clean@{tag}", ru), mels, lu, gain_db=gp)
            rec["product_gain_db"] = gp
            P.save(bp, rec)
            if m % 25 == 0:
                print(f"build {tag}: {m + 1}/{len(order)} units, {(time.time() - t0) / (m + 1):.2f} s each", flush=True)
    print(f"BUILD DONE {k}/{n}: {','.join(rows)} on {len(mine)} units")


# --- the answers (CPU, zero renders) ---------------------------------------------------------------------------------------

def cmd_predict(args):
    """A row's answers (CPU, zero renders; stage 0's phase): each read part by its fold's R-all pair from the row's stored
    features, per half, told the class and the amp, held as C3r's answers (`full_controls_c3r.cmd_predict` with only the
    input changed). A part with no features (no A2s stem, a build refused) is counted and left out; rendering a row
    needs its own stage's phase. -> ladder/answers/<row>.json."""
    from learn import full_controls_c3r as R
    from learn import local_objective as LO
    from learn import pipeline_fix as P

    rows = parse_rows(args.rows)
    require(0)                                     # answers are zero renders; a stem row's features exist only after
    for r in rows:                                 # its own stage's `sep`, which needs that stage's phase
        if row_info(r)["kind"] != "input":
            raise SystemExit(f"{r}: not an input row (`centres` makes the constants)")
    st = R.state()
    models = fold_models(st)
    ms, hold = P.A_menu_S(), R.answer_hold(st)
    units = R.read_units(st)
    for row in rows:
        out, missing = {}, []
        for ru in units:
            feats = load_feats(row, ru)
            if feats is None:
                missing.append(f"{ru['unit']}|{ru['amp']}")
                continue
            sel, S = ms[ru["amp"]][ru["prt"]["cls"]]
            for h in ("A", "B"):
                s8, ls = feats[h]
                x, c = P.vreal_model_input(s8, ls, h, ru["amp"], ru["prt"]["cls"])
                out.setdefault(ru["set"], {}).setdefault(f"{ru['unit']}|{ru['amp']}", {})[h] = {
                    "select": sel, "settings": LO.sdict(answer_of(models[ru["fold"]][0], x, c, ru["amp"], S, hold))}
        save_answers(row, out, {"c3r_sha256": st["sha256"], "models": {str(k): v[1] for k, v in models.items()},
                                "missing": missing})
        print(f"PREDICT DONE {row}: {sum(len(v) for v in out.values())} parts, {len(missing)} missing")


# --- the renders -----------------------------------------------------------------------------------------------------------

def cmd_render(args):
    """The rows' renders (one shard): each answer through the part's DI in its own primed process (`fresh_render`),
    trimmed, judged on both halves at the part's lag, as `full_controls_c3r.cmd_render`; a constant's one answer is
    rendered once and judged on both halves. -> ladder/judge/<row>/<set>/<unit>|<amp>.json."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import full_controls_c3r as R
    from learn import knob_ceiling as K
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as B
    from learn import trusted_data as T

    rows = parse_rows(args.rows)
    for r in rows:
        if row_info(r)["kind"] == "stored":
            raise SystemExit(f"{r}: C3r's stored renders")
        require(row_info(r)["stage"])
    ans = {r: json.loads(answers_path(r).read_text()) for r in rows}
    st = R.state()
    for r in rows:
        if ans[r]["c3r_sha256"] != st["sha256"]:
            raise SystemExit(f"{r}: its answers were made on another state")
    k, n = args.shard
    units = [ru for j, ru in enumerate(R.read_units(st)) if j % n == k]
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    renders = 0
    for ru in units:
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        if ru["lag"] is None:
            continue
        prt, key = ru["prt"], f"{ru['unit']}|{ru['amp']}"
        di32 = ref = di = None
        for r in rows:
            a = ans[r]["answers"].get(ru["set"], {}).get(key)
            if a is None:
                continue
            gp = judge_path(r, ru)
            asha = P.answers_sha({key: a})
            if gp.exists():
                if json.loads(gp.read_text()).get("answers_sha256") != asha:
                    raise SystemExit(f"{gp}: rendered from other answers")
                continue
            if di32 is None:
                di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
                di = np.asarray(di32, np.float64)[trim[0]:trim[1]]
                ref = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
            rec = {"set": ru["set"], "unit": ru["unit"], "amp": ru["amp"], "row": r, "lag": ru["lag"],
                   "answers_sha256": asha, "judge": {}, "render_sha256": {}}
            for search, x in sorted(a.items()):
                s_ = LO.tdict(x["settings"])
                y = np.asarray(AM.fresh_render(CB.new_renderer, di32, x["select"], s_, s_), np.float64)[trim[0]:trim[1]]
                renders += 2
                rec["judge"][search] = K.judge(ref, y, di, ru["lag"])
                rec["render_sha256"][search] = AM.audio_sha(y)
            P.save(gp, rec)
        print(f"{ru['set']} {ru['unit'][-56:]}|{ru['amp']}: renders so far {renders}", flush=True)
    print(f"LADDER-RENDER DONE {k}/{n}: {renders} renders")


def cmd_replay(_args):
    """Stage 1's render control: REPLAY_N stored R-all answers (a seeded sample of C3r's read directions) re-rendered as
    C3r rendered them; each render's sha256 must equal C3r's stored one, or old and new renders can't be compared (then
    `mix-drawn` is re-rendered under its own row). -> ladder/controls/replay.json; a mismatch stops stage 1."""
    import numpy as np

    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import full_controls_c3r as R
    from learn import local_objective as LO
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import song_bank as B

    require(1)
    st = R.state()
    stored = json.loads(R.answers_path("all").read_text())
    units = [ru for ru in R.read_units(st) if ru["lag"] is not None and R.judge_path("all", ru).exists()]
    dirs = sorted((ru["set"], ru["unit"], ru["amp"], h) for ru in units for h in ("A", "B"))
    pick = sorted(random.Random(REPLAY_SEED).sample(dirs, REPLAY_N))
    by = {(ru["set"], ru["unit"], ru["amp"]): ru for ru in units}
    trim = (int(PS.TRIM_S * PS.SR), int((PS.TRIM_S + PS.SEC_S) * PS.SR))
    LO._wait_cap()
    out = []
    for s, u, a, h in pick:
        ru = by[(s, u, a)]
        prt = ru["prt"]
        x = stored["answers"][s][f"{u}|{a}"][h]
        di32 = B.measure(PS.section_audio(prt["di_path"], prt["start_s"])).astype(np.float32)
        s_ = LO.tdict(x["settings"])
        y = np.asarray(AM.fresh_render(CB.new_renderer, di32, x["select"], s_, s_), np.float64)[trim[0]:trim[1]]
        want = json.loads(R.judge_path("all", ru).read_text())["render_sha256"][h]
        out.append({"set": s, "unit": u, "amp": a, "search": h, "equal": AM.audio_sha(y) == want})
        print(f"replay {len(out)}/{REPLAY_N}: {'equal' if out[-1]['equal'] else 'DIFFERS'}", flush=True)
    ok = all(r["equal"] for r in out)
    P.save(ladder_dir() / "controls" / "replay.json", {"renders": 2 * len(out), "equal": sum(r["equal"] for r in out),
                                                      "rows": out, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"REPLAY {'OK' if ok else 'FAILED'}: {sum(r['equal'] for r in out)} of {len(out)} renders equal ({2 * len(out)} "
          "renders)")
    if not ok:
        raise SystemExit("the replay control failed: stage 1 stops")


# --- stage 1's build controls (zero renders) -------------------------------------------------------------------------------

def cmd_check1(_args):
    """Stage 1's build controls (zero renders): (a) the stereo assembly, given S0's own layout, gains, target and draws,
    reproduces 10 stored S0 centred items (L, R, target, others; float32 to 1e-5), none of an NS or a BKS band; (b) the
    unit's amp track, levelled and mixed as D_fix's recipe, reproduces 10 stored variant-0 features exactly
    (`amp_di_compare_s.rebuild_v0`). -> ladder/controls/check1.json; a failure stops stage 1."""
    import argparse as AP
    import pathlib

    import numpy as np

    from learn import amp_di_compare_s as A2S
    from learn import cc_build as CB
    from learn import direct_sound_gate as G
    from learn import direct_stems as DS
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import sep_s0 as S0
    from learn import trusted_data as T

    require(1)
    ns = AP.Namespace(out=None, smoke=False)
    root = CB.V.out_root(ns)
    plan = {x["i"]: x for x in CB.load_plan(ns)["examples"]}
    rend = T.rows_of(root, CB.STAGE, "render")
    ctx = CB.ctx_for(ns)
    stems = T.Stems(ctx)
    items = sorted((S0.out_dir() / "items").glob("*.json"))
    pick = [p for p in items if json.loads(p.read_text())["stratum"] == "centred"
            and plan[int(p.stem)]["band"] != "BKS" and P.session_of(plan[int(p.stem)]["section"]) not in P.NS_SESSIONS][:10]
    s0 = []
    for p in pick:
        meta = json.loads(p.read_text())
        i = meta["i"]
        x, rw = plan[i], rend[i]
        y = np.asarray(G.read_flac(T.flac_path(root, CB.STAGE, i, "target"), rw["target"]["scale"],
                                   rw["target"]["sha256"]), np.float64)
        oth = np.asarray(G.read_flac(T.flac_path(root, CB.STAGE, i, "others"), rw["others_file"]["scale"],
                                     rw["others_file"]["sha256"]), np.float64)
        voc = x["draw"]["vocals_drawn"] and x["stems"]["v"] != x["stems"]["n"]
        tracks = T.backing_tracks(x, voc)
        _, gains, _ = T.self_built_mix(y, oth, np.asarray(stems.get(x["section"], tracks), np.float64), x)
        sec = ctx.sections[x["section"]]
        sess = pathlib.Path(ctx.inv[sec["di"]]["session_dir"])
        tr = [(t, *S0.load_track(sess / t, sec["start_s"], PS.SR)) for t in tracks]
        lay = S0.draw_stratum(i)
        parts = assemble(y, oth, tr, {a["track"] for a in x.get("amp_tracks") or []}, lay,
                         random.Random(f"{S0.SEED}|backing|{i}"), len(y))
        m = mixdown(parts, gains["gb"], gains["ga"], True)
        g_a, g_b = 10 ** (gains["ga"] / 20), 10 ** (gains["gb"] / 20)
        m["others"] = mid(parts["o"]) * g_b * g_a                     # S0's `others` reference: the render alone
        mastered, mrng = DS.master_draw(i)
        m = master(m, mastered, mrng, PS.SR)
        z = np.load(p.with_suffix(".npz"))
        ok = all(np.allclose(np.asarray(m[a], np.float32), z[b], atol=1e-5)
                 for a, b in (("L", "L"), ("R", "R"), ("target", "target"), ("others", "others")))
        s0.append({"i": i, "band": meta["band"], "equal": bool(ok)})
    pool = {str(e_["id"]): e_ for e_ in json.loads(P.wide_pool_path().read_text())["entries"]}
    st = R.state()
    v0 = []
    for ru in units_once(R.read_units(st)):
        if ru["set"] not in ("goat", "cap1", "panel") or len(v0) >= 10:
            continue
        try:
            got = A2S.rebuild_v0(ru["unit"], ru["prt"], pool, stems)
            v0.append({"unit": ru["unit"], "equal": got is not None})
        except SystemExit as err:
            v0.append({"unit": ru["unit"], "equal": False, "why": str(err)})
    ok = len(s0) == 10 and all(r["equal"] for r in s0) and len(v0) == 10 and all(r["equal"] for r in v0)
    P.save(ladder_dir() / "controls" / "check1.json", {"s0_items": s0, "v0_units": v0, "ok": ok,
                                                      "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"CHECK1 {'OK' if ok else 'FAILED'}: S0 items {sum(r['equal'] for r in s0)}/{len(s0)}, v0 "
          f"{sum(r['equal'] for r in v0)}/{len(v0)}")
    if not ok:
        raise SystemExit("a stage 1 build control failed: stage 1 stops")


# --- the separations (msst-venv) -------------------------------------------------------------------------------------------

def cmd_sep(args):
    """A stage's stem rows (msst-venv; separations, never beside a render): each unit's lender mixes rebuilt exactly
    (`lender_mix`; the build's mid sha256 checked), X-LANCE `gtr_mss` on full's mid (`xl@E`, the product's default) and
    on noG's mid (`xlnoG@E`), `product_path.StereoCentre` on full's stereo pair (`xlmdxc@E`), each stem at the product's
    level against its own mix; stem LUFS less mix LUFS, SI-SDR and the other guitars' leak (half A) recorded.
    -> ladder/feats/<row>/, ladder/seps/<row>/<unit>.json."""
    import argparse as AP

    import numpy as np

    from learn import cc_build as CB
    from learn import direct_existing as DE
    from learn import direct_stems as DS
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P
    from learn import pretrain_set as PS
    from learn import product_path as PP
    from learn import sep_s0 as S0
    from learn import song_aug as SA
    from learn import trusted_data as T

    rows = parse_rows(args.rows)
    for r in rows:
        if not row_info(r).get("sep"):
            raise SystemExit(f"{r}: not a stem row")
        require(row_info(r)["stage"])
    st = R.state()
    units = units_once(R.read_units(st))
    if args.subset:
        keep = set(json.loads((ladder_dir() / "subset.json").read_text())["units"])
        units = [ru for ru in units if ru["unit"] in keep]
    sep = DS.stem_separator(T.SEP, args.device)
    sep2 = PP.StereoCentre(sep) if any(r.startswith("xlmdxc@") for r in rows) else None
    e = P.require("phase_dfix")
    croot, kept, rend, _, _ = P.recipe_inputs(pin=e.get("phase_3_doubles"))
    ctx = CB.ctx_for(AP.Namespace(out=None, smoke=False))
    ld = lends()["units"]
    cache, t0, done = {}, time.time(), 0
    h = PS.half_slices()["A"]
    for ru in sorted(units, key=lambda ru: (ld[ru["unit"]]["section"], ru["unit"])):
        todo = [r for r in rows if not feat_path(r, ru).exists()]
        if not todo:
            continue
        if PS.free_gb() < T.DISK_GUARD_GB:
            raise SystemExit(f"DISK GUARD: free disk below {T.DISK_GUARD_GB:.0f} GB")
        prt = ru["prt"]
        for tag in sorted({row_info(r)["exposure"] for r in todo}):
            built = json.loads(build_path(tag, ru).read_text())
            lend = dict(ld[ru["unit"]], unit=ru["unit"])
            ref = P.real_amp_track(prt["sd"], prt["track"], prt["start_s"])
            mixes, rec = lender_mix(ctx, croot, kept, rend, cache, ref, lend, tag, PS.SR)
            same = {k_: rec[k_]["mid_sha256"] == built[k_]["mid_sha256"] for k_ in ("full", "noG")}
            for r in [r for r in todo if row_info(r)["exposure"] == tag]:
                what = r.split("@")[0]
                m = mixes["noG" if what == "xlnoG" else "full"]
                md = (m["L"] + m["R"]) / 2
                if what == "xlmdxc":
                    stem = np.asarray(sep2(np.stack([m["L"], m["R"]], 1)), np.float64)
                else:
                    stem = np.asarray(sep(md), np.float64)
                if len(stem) != len(md) or not np.isfinite(stem).all():
                    raise SystemExit(f"{ru['unit']}: bad stem ({r})")
                g = DE.inference_gain_db(md, PP.MIX_LEVEL)
                mels, lu = {}, {}
                for hh in ("A", "B"):
                    mels[hh], _, lu[hh], _ = DS.step4_half(stem, md, hh, g)
                save_feats(feat_path(r, ru), mels, lu, gain_db=g)
                P.save(ladder_dir() / "seps" / r / f"{ru['set']}__{fname(ru['unit'])}.json", {
                    "unit": ru["unit"], "row": r, "rebuild_equal": same, "gain_db": g,
                    "stem_less_mix_lufs": float(SA.lufs(stem)) - float(SA.lufs(md)),
                    "si_sdr_A": S0.si_sdr(stem[h], m["target"][h]),
                    "leak_db_A": S0.leak_db(stem[h], m["target"][h], m["guitars"][h]) if np.any(m["guitars"][h]) else None})
                done += 1
        if done % 25 == 0:
            print(f"sep: {done} stems, {(time.time() - t0) / max(1, done):.1f} s each", flush=True)
    print(f"LADDER-SEP DONE: {done} stems ({','.join(rows)})")


def cmd_subset(_args):
    """Stage 3's subset (zero renders): `subset_draw` on C3r's read units. -> ladder/subset.json."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P

    require(0)
    st = R.state()
    us = [{"set": ru["set"], "unit": ru["unit"], "fold": ru["fold"], "cls": ru["prt"]["cls"],
           "item": ru["prt"].get("item") or ru["prt"].get("di"), "creator": ru["prt"].get("creator")}
          for ru in units_once(R.read_units(st))]
    got = subset_draw(us)
    parts = [ru for ru in R.read_units(st) if ru["unit"] in set(got)]
    P.save(ladder_dir() / "subset.json", {"seed": SUBSET_SEED, "units": got, "parts": len(parts),
                                          "by_set": {s: sum(1 for u in us if u["unit"] in set(got) and u["set"] == s)
                                                     for s in SETS}})
    print(f"SUBSET: {len(got)} units, {len(parts)} parts")


# --- the reports (zero renders) --------------------------------------------------------------------------------------------

def summarise(rows_by_set, units, lender_band=None, wd=None, seen_player=None):
    """Per set: `pipeline_fix.clustered`'s row (C3r's apart rule), with beside it clean and crunch, half A alone (the
    product's half), without the heavy bands' lenders, cap1 and n12 by whether their DI's player trains in the fold;
    the deciding pool and the five-set pool (`full_controls_c3r.pooled`); one row over every set clustered by DI file.
    rows_by_set: {set: [(cluster, unit|amp, value, search)]}."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P

    keep = ("mean", "lo90", "hi90", "clusters", "clusters_negative", "part_weighted", "parts", "parts_negative")
    cls_of = {ru["unit"] + "|" + ru["amp"]: ru["prt"]["cls"] for ru in units}
    di_of = {ru["unit"] + "|" + ru["amp"]: ru["prt"]["di"] for ru in units}
    out = {}

    def cl(xs):
        return {q: P.clustered([x[:3] for x in xs]).get(q) for q in keep} if xs else None
    for s in SETS:
        main = [r for r in rows_by_set[s] if not apart(r, units, wd)]
        row = dict(cl(main) or {"mean": None}, directions=len(main))
        row["clean"] = cl([r for r in main if cls_of[r[1]] == "clean"])
        row["crunch"] = cl([r for r in main if cls_of[r[1]] == "crunch"])
        row["half_A"] = cl([r for r in main if r[3] == "A"])
        if lender_band is not None:
            row["without_heavy_lenders"] = cl([r for r in main if lender_band.get(r[1].rsplit("|", 1)[0])
                                               not in HEAVY_BANDS])
        if s in ("cap1", "n12") and seen_player is not None:
            row["player_trains"] = cl([r for r in main if r[1] in seen_player])
            row["player_unseen"] = cl([r for r in main if r[1] not in seen_player])
        ap = [r for r in rows_by_set[s] if apart(r, units, wd)]
        if ap:
            row["apart"] = cl(ap)
        out[s] = row
    panel_dis = len({ru["prt"]["di"] for ru in units if ru["set"] == "panel"})
    deciding = R.deciding_sets(panel_dis)
    out["deciding_sets"] = list(deciding)
    out["deciding_pool"] = (R.pooled({s: out[s] for s in deciding})
                            if all(out[s].get("mean") is not None for s in deciding) else None)
    out["five_set_pool"] = (R.pooled({s: out[s] for s in SETS}) if all(out[s].get("mean") is not None for s in SETS)
                            else None)
    if lender_band is not None:
        wh = {s: out[s]["without_heavy_lenders"] for s in deciding}
        out["deciding_pool_without_heavy_lenders"] = R.pooled(wh) if all(v and v.get("mean") is not None
                                                                         for v in wh.values()) else None
    every = [(di_of[r[1]], r[1], r[2], r[3]) for s in SETS for r in rows_by_set[s] if not apart(r, units, wd)]
    out["every_set_by_di_file"] = cl(every)
    return out


def decided(row):
    """'better' (90% interval wholly below 0), 'worse' (wholly above), 'undecided', or None without an interval."""
    if not row or row.get("lo90") is None or row.get("hi90") is None:
        return None
    return "better" if row["hi90"] < 0 else "worse" if row["lo90"] > 0 else "undecided"


STAGE_PAIRS = {   # (row, against): the declared rows of each stage's report; the primaries are PRIMARY's
    0: [("mix-drawn", "S"), ("mix-drawn", "RcBG"), ("mix-drawn", "RcGk"), ("mix-drawn", "Rcs2")],
    1: [("clean-kind", "cen"), ("mix@-3", "cen"), ("clean-kind", "aconst"), ("mix@-3", "aconst"),
        ("mix-drawn", "cen"), ("mix-drawn", "aconst"), ("aconst", "cen"), ("cen", "S"), ("aconst", "S"),
        ("clean-kind", "S"), ("mix@-3", "S"), ("mix@-3", "mix-drawn"), ("clean-kind", "mix-drawn"),
        ("clean-kind", "mix@-3"), ("label", "cen")],
    2: [("xl@-3", "cen"), ("xlnoG@-3", "mix@-3"), ("xl@-3", "xlnoG@-3"), ("xl@-3", "aconst"), ("xl@-3", "S"),
        ("clean@-3", "xl@-3"), ("clean@-3", "cen"), ("xl-v0", "mix-drawn"), ("xl@-3", "mix@-3")],
}
PRIMARY = {1: [("clean-kind", "cen"), ("mix@-3", "cen"), ("clean-kind", "aconst"), ("mix@-3", "aconst")],
           2: [("xl@-3", "cen"), ("xlnoG@-3", "mix@-3"), ("xl@-3", "xlnoG@-3")]}
LENDER_ROWS = ("mix@", "full@", "clean@", "xl@", "xlnoG@", "xlmdxc@")


def value_fn(st, name):
    if name == "S":
        return val_s(st)
    if name == "label":
        return val_label(st)
    if name in ("RcBG", "RcGk", "Rcs2"):
        return val_centre(name)
    return val_row(name)


def cmd_report(args):
    """A stage's report (zero renders): every declared pair of that stage (`STAGE_PAIRS`), ln(d_row / d_against) on the
    held half, per set and pooled with C3r's rules (`summarise`); beside each, the share of the Cen-to-label gap it closes
    and the missing directions; the primaries' outcome (`decided`). -> ladder/report-stage<n>.json."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P

    require(args.stage)
    if args.stage not in STAGE_PAIRS:
        raise SystemExit(f"stage {args.stage}'s rows are declared with its ledger phase (STAGE_PAIRS)")
    st = R.state()
    units = R.read_units(st)
    ld = lends()["units"] if (ladder_dir() / "lends.json").exists() else {}
    band = {u: v["band"] for u, v in ld.items()}
    seen = R.player_seen(st, units)
    fns = {}
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASES[args.stage]}", "stage": args.stage, "rows": {}}
    cen_vals = None
    for a, b in STAGE_PAIRS[args.stage]:
        for nm in (a, b):
            if nm not in fns:
                fns[nm] = value_fn(st, nm)
        got = rows_for_pair(st, units, fns[a], fns[b])
        lb = band if any(a.startswith(p) or b.startswith(p) for p in LENDER_ROWS) else None
        row = summarise(got, units, lb, seen_player=seen)
        row["directions_read"] = sum(len(v) for v in got.values())
        if b == "cen" and a != "label":
            if cen_vals is None:
                cen_vals = {s: {(r[1], r[3]): r[2] for r in v} for s, v in
                            rows_for_pair(st, units, value_fn(st, "label"), fns["cen"]).items()}
            row["gap_share"] = {s: dict(zip(("share", "directions"), gap_share({(r[1], r[3]): r[2] for r in got[s]},
                                                                                cen_vals[s]))) for s in SETS}
        out["rows"][f"{a} - {b}"] = row
    out["primaries"] = {f"{a} - {b}": decided(out["rows"][f"{a} - {b}"]["deciding_pool"])
                        for a, b in PRIMARY.get(args.stage, [])}
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(ladder_dir() / f"report-stage{args.stage}.json", out)
    for name, row in out["rows"].items():
        dp = row.get("deciding_pool") or {}
        print(f"{name}: pool {dp.get('mean')} [{dp.get('lo90')}, {dp.get('hi90')}]; "
              + "; ".join(f"{s} {(row[s] or {}).get('mean')}" for s in SETS))
    print("PRIMARIES", json.dumps(out["primaries"]))


# --- stage 0 (zero renders) ------------------------------------------------------------------------------------------------

def v0_ratios(st, units):
    """Per unit, the stored variant-0 input's levels: the lender's drawn guitar-to-backing ratio (against a backing that
    held its own other guitars) and the stored input's own target-to-backing ratio (the levelled target less the backing
    as mixed, before mastering). -> {unit: {"drawn": dB, "v0": dB or None}}."""
    import numpy as np

    from learn import pipeline_fix as P

    e = P.require("phase_dfix")
    _, kept, _, _, _ = P.recipe_inputs(pin=e.get("phase_3_doubles"))
    pool = {str(x["id"]): x for x in json.loads(P.wide_pool_path().read_text())["entries"]}
    own_lv = json.loads((P.out_dir() / "inputs" / "backings-levels.json").read_text())["levels"]
    out = {}
    for ru in units_once(units):
        d = np.load(P.dfix_input_path(ru["unit"], 0))
        bid, voc = str(d["backing"]), str(bool(d["vocals"]))
        lv = pool[bid]["lufs"][voc] if bid in pool else (own_lv.get(bid) or {}).get(voc)
        gb = float(d["gains"][0])
        out[ru["unit"]] = {"drawn": kept[int(d["lend"])]["draw"]["ratio_db"],
                           "v0": None if lv is None else float(d["target_lufs"]) - (float(lv) + gb)}
    return out


def knob_values(settings, amp, label=None):
    """{head name: unit value} of the K.space continuous heads in KNOB_GROUPS that sound in the setting."""
    from learn import full_space as F
    from learn import local_objective as LO

    x = LO.tdict(settings)
    c, cm, *_ = F.encode(x, amp)
    D = F.by_name()
    want = {k for v in KNOB_GROUPS.values() for k in v}
    return {n: float(c[j]) for j, n in enumerate(F.CONT) if cm[j] > 0 and D[n].key in want}


def group_of(name):
    from learn import full_space as F

    key = F.by_name()[name].key
    return next(g for g, v in KNOB_GROUPS.items() if key in v)


def knob_read(st, units, answers_by_row):
    """Stage 0's knob-space reads (descriptive): per row and group, the within-cell r of the answers with the labels
    (cells: set, fold, amp, class and head), the answers' within-cell spread against the labels', and the share of
    knob values where the answer is farther from the label than the cell's mean label of the other clusters is; per
    pair of input rows, how far a unit's answer moves between the inputs against how far answers differ between units."""
    from learn import local_objective as LO

    src = st["sources"]
    labs = {}
    for ru in units:
        s = src.get((ru["unit"], ru["amp"]))
        if s is not None:
            labs[(ru["unit"], ru["amp"])] = knob_values(LO.sdict(LO.tdict(s["label"])), ru["amp"])
    out = {"rows": {}, "moves": {}}
    vals = {}
    for row, ans in answers_by_row.items():
        per = []
        for ru in units:
            a = ans.get(ru["set"], {}).get(f"{ru['unit']}|{ru['amp']}")
            lab = labs.get((ru["unit"], ru["amp"]))
            if a is None or lab is None:
                continue
            for h, x in a.items():
                av = knob_values(x["settings"], ru["amp"])
                for n, v in av.items():
                    if n in lab:
                        cell = (ru["set"], ru["fold"], ru["amp"], ru["prt"]["cls"], n)
                        per.append((cell, (ru["unit"], ru["amp"], h), ru["cluster"], n, v, lab[n]))
        vals[row] = per
        res = {}
        for g in KNOB_GROUPS:
            xs = [p for p in per if group_of(p[3]) == g]
            da = within_cell([(p[0], p[1] + (p[3],), p[4]) for p in xs])
            dl = within_cell([(p[0], p[1] + (p[3],), p[5]) for p in xs])
            ks = sorted(set(da) & set(dl))
            sd = lambda d: math.sqrt(sum(d[k] ** 2 for k in ks) / len(ks)) if ks else None   # noqa: E731
            by_cell = {}
            for p in xs:
                by_cell.setdefault(p[0], []).append(p)
            lose = n_ = 0
            for p in xs:
                others = [q[5] for q in by_cell[p[0]] if q[2] != p[2]]
                if not others:
                    continue
                n_ += 1
                lose += abs(p[4] - p[5]) > abs(sum(others) / len(others) - p[5])
            res[g] = {"values": len(ks), "r_within_cell": corr([da[k] for k in ks], [dl[k] for k in ks]),
                      "answer_spread_over_label_spread": (sd(da) / sd(dl)) if ks and sd(dl) else None,
                      "loses_to_cell_mean": lose / n_ if n_ else None}
        out["rows"][row] = res
    names = [r for r in answers_by_row if r not in ("cen", "aconst")]
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            va = {(p[1], p[3]): (p[0], p[4]) for p in vals[a]}
            vb = {(p[1], p[3]): p[4] for p in vals[b]}
            ks = sorted(set(va) & set(vb))
            if not ks:
                continue
            mv = math.sqrt(sum((va[k][1] - vb[k]) ** 2 for k in ks) / len(ks))
            dev = within_cell([(va[k][0], k, va[k][1]) for k in ks])
            between = math.sqrt(sum(v ** 2 for v in dev.values()) / len(dev)) if dev else None
            out["moves"][f"{a} vs {b}"] = {"values": len(ks), "rms_move": mv, "rms_between_units": between}
    return out


def r1_exposures():
    """R1's seven songs' model-path windows: stem LUFS less mix LUFS (metadata only, no audio), sorted, no titles."""
    from learn import pipeline_fix as P

    d = P.out_dir() / "r1"
    songs = json.loads((d / "songs.json").read_text())["songs"]
    out = []
    for slug in sorted(songs):
        p = d / str(slug) / "window.json"
        if p.exists():
            w = json.loads(p.read_text())
            out.append({"exposure_db": (w.get("window") or {}).get("exposure_db"), "version": w.get("version")})
    return sorted(out, key=lambda r: r["exposure_db"] if r["exposure_db"] is not None else 0.0)


def cmd_stage0(_args):
    """Stage 0's read (zero renders): the planner's preview reproduced (R-all on its stored input against S and 5C's core
    centres, per set, and by each unit's guitar-to-backing ratio, the lender's drawn one and the stored input's own),
    the knob-space reads of every row with answers, the lenders' counts and R1's seven exposures beside.
    -> ladder/report-stage0.json."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P

    require(0)
    st = R.state()
    units = R.read_units(st)
    rat = v0_ratios(st, units)
    out = {"plan": PLAN, "ledger": f"{LEDGER_ID} {PHASES[0]}", "stage": 0, "rows": {}, "by_ratio": {}}
    for a, b in STAGE_PAIRS[0]:
        got = rows_for_pair(st, units, value_fn(st, a), value_fn(st, b))
        out["rows"][f"{a} - {b}"] = summarise(got, units)
        for which in ("drawn", "v0"):
            res = {}
            for s in ("goat", "bks"):
                by = {}
                for r in got[s]:
                    by.setdefault(ratio_bin(rat[r[1].rsplit("|", 1)[0]][which]), []).append(r)
                res[s] = {k: {q: P.clustered([x[:3] for x in v]).get(q) for q in ("mean", "lo90", "hi90", "clusters",
                                                                                  "parts")}
                          for k, v in sorted(by.items(), key=lambda kv: str(kv[0]))}
                cm = {}
                for r in got[s]:
                    cm.setdefault(r[0], []).append((rat[r[1].rsplit("|", 1)[0]][which], r[2]))
                xs = [sum(x for x, _ in v) / len(v) for v in cm.values() if all(x is not None for x, _ in v)]
                ys = [sum(y for _, y in v) / len(v) for v in cm.values() if all(x is not None for x, _ in v)]
                res[s]["slope_per_db_over_cluster_means"] = slope(xs, ys)
            out["by_ratio"].setdefault(f"{a} - {b}", {})[which] = res
    ratios = [v["v0"] for v in rat.values() if v["v0"] is not None]
    out["v0_ratio_quartiles"] = sorted(ratios)[len(ratios) // 4], sorted(ratios)[len(ratios) // 2], \
        sorted(ratios)[3 * len(ratios) // 4]
    dr = sorted(v["drawn"] for v in rat.values())
    out["drawn_ratio_quartiles"] = dr[len(dr) // 4], dr[len(dr) // 2], dr[3 * len(dr) // 4]
    ans = {"mix-drawn": json.loads(R.answers_path("all").read_text())["answers"]}
    for r in ("cen", "aconst", "clean-kind", "xl-v0"):
        if answers_path(r).exists():
            ans[r] = json.loads(answers_path(r).read_text())["answers"]
    out["knob_read"] = knob_read(st, units, ans)
    if (ladder_dir() / "lends.json").exists():
        L = lends()
        out["lenders"] = {k: L[k] for k in ("candidates", "pool", "silent_out", "lent_by")}
    out["r1_exposures"] = r1_exposures()
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(ladder_dir() / "report-stage0.json", out)
    for name, row in out["rows"].items():
        print(name, {s: (row[s] or {}).get("mean") for s in ("goat", "bks")})
    print("STAGE0 DONE")


def main(argv=None):
    from learn import full_controls as F

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("lends").set_defaults(fn=cmd_lends)
    sub.add_parser("check0").set_defaults(fn=cmd_check0)
    sub.add_parser("centres").set_defaults(fn=cmd_centres)
    sub.add_parser("subset").set_defaults(fn=cmd_subset)
    b = sub.add_parser("build")
    b.add_argument("--rows", required=True)
    b.add_argument("--shard", type=F.shard, default=(0, 1))
    b.set_defaults(fn=cmd_build)
    p = sub.add_parser("predict")
    p.add_argument("--rows", required=True)
    p.set_defaults(fn=cmd_predict)
    sub.add_parser("stage0").set_defaults(fn=cmd_stage0)
    sub.add_parser("check1").set_defaults(fn=cmd_check1)
    sub.add_parser("replay").set_defaults(fn=cmd_replay)
    r = sub.add_parser("render")
    r.add_argument("--rows", required=True)
    r.add_argument("--shard", type=F.shard, default=(0, 1))
    r.set_defaults(fn=cmd_render)
    s = sub.add_parser("sep")
    s.add_argument("--rows", required=True)
    s.add_argument("--device", default="mps")
    s.add_argument("--subset", action="store_true", help="stage 3's subset only")
    s.set_defaults(fn=cmd_sep)
    q = sub.add_parser("report")
    q.add_argument("--stage", type=int, choices=(1, 2, 3), required=True)
    q.set_defaults(fn=cmd_report)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
