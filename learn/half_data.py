"""The learning-curve diagnostic (`docs/half-data-plan.md`; Step 6 plan section 14; ledger `pipeline-fix`
`phase_s6_half`, `preset-ladder` `phase_l6_half`): R-all's recipe trained on half the chains of each set, read on the
ladder's stored `xl@-3`, raw and re-centred. It asks whether more distinct recordings would make the model better.

    $TORCH_PY -m learn.half_data select          # the two complementary halves (zero renders) -> PF/step6/half/
    zsh learn/half_data_train.zsh                # 32 runs, one MPS job at a time (`pipeline_fix train-ft --c3r-half`)
    $TORCH_PY -m learn.half_data answers         # half-a-xl@-3, half-b-xl@-3, their constants and re-centred rows
    .venv/bin/python -m learn.preset_ladder render --rows half-a-xl@-3,rc-half-a-xl@-3,half-b-xl@-3,rc-half-b-xl@-3 \\
        --shard 0/3                              # ... three shards
    .venv/bin/python -m learn.half_data report   # D_TABLE's cell, read only after the rows are saved

**The design (training noise).** Two half arms on complementary halves of the chains, H_A and its complement H_B, each
fold run starting from the same W state and with the same fine-tune seed as one full-data model already trained:
arm a (H_A) as R-all (seeds 20261042, 20261043), arm b (H_B) as R-rep (20261181, 20261182). W saw no real row, so
sharing its states leaks no recording. The decision row H is both halves' mean against both full models' mean, per
direction (`geo`); its seed noise is sampled on both sides: R-rep against R-all (the fine-tune seed alone) and arm b
against arm a (the seed and which half). Each half's matched row (H_a, H_b) must read as H does (the noise check).

**The user's rule (2026-11-19).** No action rests on a gap under 0.05. `heard_reading` reads a row "cost" only when it
is decided worse and its lower end is over 0.05 or its mean is 0.10 or more, and "unreadable" when its interval sits
inside +-0.05 ("not readable by the score").

`D_TABLE` and its guard are declared here, before any run, and tested in `tests/test_half_data.py`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time

PLAN = "docs/half-data-plan.md"
PHASE_HALF = "phase_s6_half"                    # ledger pipeline-fix: the selection and the 32 runs
PHASE_L6_HALF = "phase_l6_half"                 # ledger preset-ladder: the answers, renders and report
OUT = "half"                                    # PF/step6/half/
FOLDS = 4
SETS = ("bks", "goat", "cap1", "n12", "panel")
HALF_SEED = 20261191                            # the halves' draws: one seed, a draw counter
MAX_DRAWS = 1000
BALANCE = (0.4, 0.6)                            # each set's kept share of its records, in both halves
BALANCE_MIN_CHAINS = 4                          # ... for sets with at least this many chains
ARMS = {"a": {"half": "A", "base": "C3r-half-a", "seeds": {20261042: 20261042, 20261043: 20261043}, "like": "xl@-3"},
        "b": {"half": "B", "base": "C3r-half-b", "seeds": {20261181: 20261042, 20261182: 20261043},
              "like": "rep-xl@-3"}}             # arm: its half, base, {fine-tune seed: W's seed}, its matched model row
HALF_RATE = (1e-4, 300)                         # R-all's (lr, cap)
PROTECTED_BASES = ("C3r-all", "C3r-ctl", "C3r-allK", "C3r-ctlK", "C3r-rep", "C3r-replay")
SMALL = 0.05                                    # the user's rule: no action rests on a gap under this
BIG = 0.10                                      # by ear the score is trusted at gaps of about this and over
GOAL_VS_CEN = -0.06                             # where a row against Cen reads better (the Step 6 plan's figure)
READINGS = ("better", "undecided", "worse")
HEARD = ("cost", "gain", "unreadable", "short")
NOISE = ("holds", "fails")

# the rows: models' answers on the stored xl@-3 (`preset_ladder.L6_HALF_MODEL_ROWS`), re-centred by the ladder's rule
HALF_ROWS = {"half-a-xl@-3": "a", "half-b-xl@-3": "b"}
RC_HALF_ROWS = {"rc-half-a-xl@-3": "half-a-xl@-3", "rc-half-b-xl@-3": "half-b-xl@-3"}
FULL_RC, FULL_RAW = ("rc-xl@-3", "rc-rep-xl@-3"), ("xl@-3", "rep-xl@-3")     # the full arm: R-all and R-rep
HALF_RC, HALF_RAW = ("rc-half-a-xl@-3", "rc-half-b-xl@-3"), ("half-a-xl@-3", "half-b-xl@-3")
D_ROWS = {                                       # name: (row a, row b); a "+" joins rows averaged per direction (`geo`)
    "H": ("+".join(HALF_RC), "+".join(FULL_RC)),                 # the decision row
    "H_a": ("rc-half-a-xl@-3", "rc-xl@-3"),                      # arm a against R-all (same W states and seeds)
    "H_b": ("rc-half-b-xl@-3", "rc-rep-xl@-3"),                  # arm b against R-rep (same W states and seeds)
}
D_BESIDE = {
    "H raw": ("+".join(HALF_RAW), "+".join(FULL_RAW)),
    "H_a raw": ("half-a-xl@-3", "xl@-3"),
    "H_b raw": ("half-b-xl@-3", "rep-xl@-3"),
    "H_a x": ("rc-half-a-xl@-3", "rc-rep-xl@-3"),
    "H_b x": ("rc-half-b-xl@-3", "rc-xl@-3"),
    "half spread": ("rc-half-b-xl@-3", "rc-half-a-xl@-3"),       # the seed and which half
    "full spread": ("rc-rep-xl@-3", "rc-xl@-3"),                 # the fine-tune seed alone (stage N's beside row)
    "half raw spread": ("half-b-xl@-3", "half-a-xl@-3"),
    "full vs cen": ("+".join(FULL_RC), "cen"),                   # where the full arm sits against Cen
    "half vs cen": ("+".join(HALF_RC), "cen"),
}

# trusted data: the panel's Silent Waves parts carry vocal bleed (the ladder's ear check, card i14) and await a
# trusted-data review, so every row above is read without them; the same band's Drowning awaits a bleed check. Beside:
# H with every part, and H without both recordings. Training keeps R-all's rows (see the plan, section 4).
EXCLUDED_READ = ("Silent Waves",)               # panel DI titles left out of the read
BAND_BESIDE = ("Silent Waves", "Drowning")      # the band's two recordings, left out of one beside row


def title_of(ru):
    """A read part's panel DI title (the last part of its library DI id), else None."""
    return ru["prt"]["di"].rsplit("/", 1)[-1] if ru["set"] == "panel" else None


def read_parts(units, leave_out=EXCLUDED_READ):
    """(Pure.) The read's parts less the panel's left-out recordings."""
    return [ru for ru in units if title_of(ru) not in leave_out]


D_TABLE = (                     # (H's heard readings, noise check, code, next): each of the 8 pairs once
    (("cost",), ("holds",), "D-data",
     "halving the chains costs a heard-size amount by the score, on the product's input, beyond the seed spread. More "
     "chains is a live lever, and this is its first size. The write-up gives the doublings the measured cost would need "
     "to reach about -0.06 against Cen (constant gain per doubling: a lower bound if returns diminish). To the user with "
     "the supply limit"),
    (("cost", "gain"), ("fails",), "D-noise",
     "not separable from training noise: one half's matched row does not read as H does. Reported with both spreads; "
     "nothing follows"),
    (("gain",), ("holds",), "D-odd",
     "fewer chains reads better by a heard-size amount: an early stop or which half, not a finding. Reported; nothing "
     "follows"),
    (("unreadable",), NOISE, "D-unreadable",
     "not readable by the score: H's interval sits inside +-0.05. Halving is not shown to cost a heard-size amount, so, "
     "if returns per doubling do not grow, doubling the chains is not shown to buy one either; the limit is more likely "
     "the labels or the reading. To the user; no action rests on it"),
    (("short",), NOISE, "D-short",
     "not decided at a heard size: the interval reaches past +-0.05 with no counted gap (underpowered, or a decided gap "
     "under the user's rule). No action; the write-up gives what the interval rules out"))


# --- the tables (pure) -----------------------------------------------------------------------------------------------------

def table_guard():
    """Refuse unless D_TABLE holds each (heard reading, noise) pair exactly once, with the five declared codes."""
    for h in HEARD:
        for n in NOISE:
            if sum(h in hs and n in ns for hs, ns, _, _ in D_TABLE) != 1:
                raise SystemExit(f"D_TABLE holds ({h}, {n}) not once")
    if {c for *_, c, _ in D_TABLE} != {"D-data", "D-noise", "D-odd", "D-unreadable", "D-short"}:
        raise SystemExit("D_TABLE's codes are not the five declared")
    if not 0 < SMALL < BIG:
        raise SystemExit("the heard-size thresholds are not 0 < SMALL < BIG")


def decided(row):
    """'better' (90% interval wholly below 0), 'worse' (wholly above), 'undecided'; None without an interval."""
    if not row or row.get("lo90") is None or row.get("hi90") is None:
        return None
    return "better" if row["hi90"] < 0 else "worse" if row["lo90"] > 0 else "undecided"


def heard_reading(row, small=SMALL, big=BIG):
    """(Pure.) A row's reading under the user's rule: "cost" (decided worse, and its lower end over `small` or its mean
    `big` or more), "gain" (the mirror), "unreadable" (the interval inside +-small: not readable by the score), "short"
    (the rest: it reaches past +-small with no counted gap). None without an interval."""
    d = decided(row)
    if d is None:
        return None
    lo, hi, m = row["lo90"], row["hi90"], row["mean"]
    if d == "worse" and (lo > small or m >= big):
        return "cost"
    if d == "better" and (hi < -small or m <= -big):
        return "gain"
    if lo >= -small and hi <= small:
        return "unreadable"
    return "short"


def noise_check(heard, h_a, h_b):
    """(Pure.) For a counted H ("cost" or "gain"): both halves' matched rows decided the same way as H. Else "holds"."""
    if heard not in ("cost", "gain"):
        return "holds"
    want = "worse" if heard == "cost" else "better"
    return "holds" if decided(h_a) == want and decided(h_b) == want else "fails"


def d_cell(heard, noise):
    """(Pure.) D_TABLE's row. -> (code, next)."""
    table_guard()
    hit = [(c, t) for hs, ns, c, t in D_TABLE if heard in hs and noise in ns]
    if len(hit) != 1:
        raise SystemExit(f"D_TABLE has {len(hit)} rows for H {heard}, noise {noise}")
    return hit[0]


def doublings(gap_now, cost, goal=GOAL_VS_CEN):
    """(Pure.) Doublings of the chains a constant gain of `cost` a doubling would need to bring a row against Cen from
    `gap_now` to `goal`. None when the cost is not a gain (<= 0); 0 when already there."""
    if cost is None or gap_now is None or cost <= 0:
        return None
    return max(0.0, (gap_now - goal) / cost)


def d_outcome(rows):
    """(Pure.) The cell from the report's rows ({name: {"deciding_pool": row}}): H by `heard_reading`, the noise check
    on H_a and H_b, D_TABLE; for D-data the doublings to the goal (by H's mean and its interval's ends, with the full
    arm's pooled row against Cen). A missing H refuses."""
    def dp(name):
        return (rows.get(name) or {}).get("deciding_pool")
    h = dp("H")
    heard = heard_reading(h)
    if heard is None:
        raise SystemExit("H: no reading (the report is incomplete)")
    noise = noise_check(heard, dp("H_a"), dp("H_b"))
    code, nxt = d_cell(heard, noise)
    out = {"H": {k: h.get(k) for k in ("mean", "lo90", "hi90")}, "decided": decided(h), "heard": heard,
           "noise": noise, "H_a": decided(dp("H_a")), "H_b": decided(dp("H_b")), "code": code, "next": nxt}
    if code == "D-data":
        cen = (dp("full vs cen") or {}).get("mean")
        out["doublings_to_goal"] = {"goal_vs_cen": GOAL_VS_CEN, "full_vs_cen": cen,
                                    "at_mean": doublings(cen, h["mean"]), "at_hi90": doublings(cen, h["hi90"]),
                                    "at_lo90": doublings(cen, h["lo90"]),
                                    "assumption": "a constant gain per doubling; if returns diminish, more are needed"}
    return out


# --- the halves (pure on C3r's entries) -----------------------------------------------------------------------------------

def chains_of(entries, prt_of):
    """(Pure.) C3r's training units grouped by chain (`prt["rig"]`: BKS a DI file and reamp track, GOAT a capture
    render, cap1 and n12 a capture, the panel a DI file and amp track), each with its set, fold and class (the units'
    most common, ties by name). `prt_of(entry)` -> the unit's dict. -> {(set, chain): {"set", "chain", "fold", "cls",
    "units"}}."""
    out = {}
    for e in entries:
        if not e["row"]:
            continue
        prt = prt_of(e)
        c = out.setdefault((e["set"], prt["rig"]), {"set": e["set"], "chain": prt["rig"], "folds": set(), "cls": [],
                                                    "units": []})
        c["folds"].add(e["fold"])
        c["cls"].append(prt["cls"])
        c["units"].append(e["unit"])
    for k, c in out.items():
        if len(c["folds"]) != 1:
            raise SystemExit(f"{k}: a chain over several folds")
        c["fold"] = c.pop("folds").pop()
        cnt = {}
        for x in c["cls"]:
            cnt[x] = cnt.get(x, 0) + 1
        c["cls"] = sorted(cnt, key=lambda x: (-cnt[x], x))[0]
        c["units"] = sorted(c["units"])
    return out


def draw(chains, j, seed=HALF_SEED):
    """(Pure.) Draw j of half A: in each (set, fold, class) stratum the chains shuffled by a seeded generator, the first
    floor(n / 2) kept, and an odd stratum's middle chain kept on a seeded coin. Half B is the complement. -> the kept
    chain keys, sorted."""
    strata = {}
    for k, c in chains.items():
        strata.setdefault((c["set"], c["fold"], c["cls"]), []).append(k)
    kept = []
    for s in sorted(strata):
        ks = sorted(strata[s])
        rng = random.Random(f"{seed}|{j}|{s[0]}|{s[1]}|{s[2]}")
        rng.shuffle(ks)
        n = len(ks) // 2 + (1 if len(ks) % 2 and rng.random() < 0.5 else 0)
        kept += ks[:n]
    return sorted(kept)


def run_units(entries, k, inner):
    """C3r's training units of one fold run (`full_controls_c3r.split`, arm all). -> set of unit names."""
    from learn import full_controls_c3r as R

    return {e["unit"] for e in R.split(entries, k, inner, "all")[0]}


def guard(chains, kept, entries, records, cls_of, amp_cells=None):
    """(Pure on its inputs.) Why a half pair is refused, or []: in every fold run (FT_k and inner, k 0..3), each half
    keeps at least one training record of every set the full run trains on two chains or more (one chain can't be in
    both halves) and of every pooled (amp, class) cell the full run trains; and in
    each half every set with at least BALANCE_MIN_CHAINS chains keeps a share of its records within BALANCE.
    `records` {unit: [amp]}, `cls_of` {unit: class}."""
    unit_chain = {u: key for key, c in chains.items() for u in c["units"]}
    a = {u for key in kept for u in chains[key]["units"]}
    b = set(unit_chain) - a
    set_of = {u: chains[unit_chain[u]]["set"] for u in unit_chain}
    bad = []
    for k in range(FOLDS):
        for inner in (False, True):
            full = run_units(entries, k, inner)
            tag = f"{'inner' if inner else 'FT'}_k{k}"
            n_ch = {}
            for key in {unit_chain[u] for u in full}:
                n_ch[chains[key]["set"]] = n_ch.get(chains[key]["set"], 0) + 1
            for name, half in (("A", a), ("B", b)):
                hu = full & half
                for s in sorted(q for q, n in n_ch.items() if n >= 2):     # one chain can't be in both halves
                    if not any(set_of[u] == s for u in hu):
                        bad.append(f"{tag} half {name}: no {s} record")
                cells = {(amp, cls_of[u]) for u in full for amp in records[u]}
                got = {(amp, cls_of[u]) for u in hu for amp in records[u]}
                for c in sorted(cells - got):
                    bad.append(f"{tag} half {name}: no ({c[0]}, {c[1]}) record")
    for s in SETS:
        keys = [key for key, c in chains.items() if c["set"] == s]
        if len(keys) < BALANCE_MIN_CHAINS:
            continue
        tot = sum(len(records[u]) for key in keys for u in chains[key]["units"])
        ka = sum(len(records[u]) for key in keys if key in set(kept) for u in chains[key]["units"])
        share = ka / tot
        if not (BALANCE[0] <= share <= BALANCE[1]):
            bad.append(f"{s}: half A keeps {share:.3f} of its records, outside {BALANCE}")
    return bad


def choose(chains, entries, records, cls_of, seed=HALF_SEED, max_draws=MAX_DRAWS):
    """(Pure on its inputs.) The first draw (j = 0, 1, ...) whose halves pass `guard`. -> (j, kept, problems of the
    draws refused, counted)."""
    refused = {}
    for j in range(max_draws):
        kept = draw(chains, j, seed)
        bad = guard(chains, kept, entries, records, cls_of)
        if not bad:
            return j, kept, refused
        for b in bad:
            key = b.split(":")[0].split(" half ")[0] if " half " in b else b.split(":")[0]
            refused[key] = refused.get(key, 0) + 1
    raise SystemExit(f"no draw of {max_draws} passes the guard: {sorted(refused.items())[:5]}")


def selection_sha(sel):
    """The selection's content hash: its two halves' chain keys and units, canonical JSON."""
    body = {h: {"chains": sel["halves"][h]["chains"], "units": sel["halves"][h]["units"]} for h in ("A", "B")}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


# --- the runs' refusals (pure) ---------------------------------------------------------------------------------------------

def arm_of_base(base):
    return next((a for a, v in ARMS.items() if v["base"] == base), None)


def half_w_seed(arm, seed):
    return ARMS[arm]["seeds"][seed]


def half_inner_keys(arm):
    """The (fold, seed) inner runs an arm's FT_k reads its E from: its own eight."""
    return [(q, sd) for q in range(FOLDS) for sd in ARMS[arm]["seeds"]]


def half_refusal(arm, c3r, k, inner, seed, base, rep=None):
    """(Pure.) Why `train-ft --c3r-half` may not run, or None: R-all's recipe only (C3r's arm `all` on C3's recipe), a
    fold run (no all-labels pair), the arm's own seeds, and not with --c3r-rep."""
    if arm not in ARMS:
        return f"--c3r-half in {tuple(ARMS)}"
    if rep is not None:
        return "--c3r-half and --c3r-rep are separate runs"
    if c3r != "all" or base != "C3r-all":
        return "--c3r-half trains R-all's recipe only: --c3r all on C3's recipe"
    if k is None:
        return "--c3r-half trains fold runs only: the diagnostic has no all-labels pair"
    if seed not in ARMS[arm]["seeds"]:
        return f"--c3r-half {arm}: --seed in {tuple(ARMS[arm]['seeds'])}"
    return None


def half_write_refusal(arm, name, seed, inner, exists):
    """(Pure on `exists`.) Why a half run may not start, or None: its name is its arm's base's and no protected base's,
    and none of the files it would write exist (never overwritten). Checked before any work."""
    base = ARMS[arm]["base"]
    if not (name == base or name.startswith(base + "-")):
        return f"{name}: not arm {arm}'s name (base {base})"
    if any(name == b or name.startswith(b + "-") for b in PROTECTED_BASES):
        return f"{name}: a protected base's name"
    files = [f"{name}-{seed}.json"] + ([] if inner else [f"{name}-{seed}-final.pt"])
    there = [f for f in files if exists(f)]
    if there:
        return f"{name}: {there} already exist; move them aside first (never overwritten)"
    return None


def keep_filter(training_entries, keep_units):
    """(Pure.) C3r's training entries of a run less every unit outside the half. Held and dropped entries unchanged."""
    return [e for e in training_entries if e["unit"] in keep_units]


# --- the per-direction mean of rows (pure) ---------------------------------------------------------------------------------

def geo(fns):
    """(Pure.) A value function whose distance is the geometric mean of several rows' (None when any is missing), so
    ln(geo(a1, a2) / geo(b1, b2)) is the mean of ln(a1 / b1) and ln(a2 / b2): both halves against both full models."""
    def f(ru, sh, h):
        vs = [g(ru, sh, h) for g in fns]
        if any(v is None or not v > 0 for v in vs):
            return None
        return math.exp(sum(math.log(v) for v in vs) / len(vs))
    return f


# --- the commands ------------------------------------------------------------------------------------------------------

def half_dir():
    from learn import stem_finetune as S6

    return S6.step6_dir() / OUT


def require_all():
    from learn import pipeline_fix as P
    from learn import preset_ladder as L

    table_guard()
    P.require(PHASE_HALF)
    L.require_phase(PHASE_L6_HALF)


def real_selection(st):
    """C3r's chains, records and classes for the guard. -> (chains, entries, records, cls_of)."""
    ents = st["entries"]
    chains = chains_of(ents, lambda e: st["units"][e["set"]][e["unit"]])
    records = {}
    for (u, amp) in st["sources"]:
        records.setdefault(u, []).append(amp)
    cls_of = {e["unit"]: st["units"][e["set"]][e["unit"]]["cls"] for e in ents if e["row"]}
    return chains, ents, records, cls_of


def selection_summary(chains, kept, entries, records):
    """Per half: chains, units and records per set; per fold run: training units and records per set."""
    unit_chain = {u: key for key, c in chains.items() for u in c["units"]}
    halves = {"A": {u for key in kept for u in chains[key]["units"]}}
    halves["B"] = set(unit_chain) - halves["A"]
    out = {}
    for h, us in halves.items():
        keys = sorted({unit_chain[u] for u in us})
        per = {s: {"chains": sum(1 for q in keys if chains[q]["set"] == s),
                   "units": sum(1 for u in us if chains[unit_chain[u]]["set"] == s),
                   "records": sum(len(records[u]) for u in us if chains[unit_chain[u]]["set"] == s)} for s in SETS}
        runs = {}
        for k in range(FOLDS):
            for inner in (False, True):
                full = run_units(entries, k, inner)
                runs[f"{'inner' if inner else 'FT'}_k{k}"] = {
                    s: [sum(len(records[u]) for u in full & us if chains[unit_chain[u]]["set"] == s),
                        sum(len(records[u]) for u in full if chains[unit_chain[u]]["set"] == s)] for s in SETS}
        out[h] = {"chains": [list(q) for q in keys], "units": sorted(us), "per_set": per,
                  "runs (kept, full) records": runs}
    return out


def selection_path():
    return half_dir() / "selection.json"


def cmd_select(_args):
    """The two halves (zero renders, CPU; `phase_s6_half`): the first draw that passes the guard, saved once
    (never overwritten), with its content hash and per-set and per-run counts. -> PF/step6/half/selection.json."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P
    from learn import stem_finetune as S6

    require_all()
    s0 = S6.stage0_ok()
    st = R.state()
    if st["sha256"] != s0["c3r_sha256"]:
        raise SystemExit("C3r's state changed since Step 6's stage 0")
    p = selection_path()
    if p.exists():
        raise SystemExit(f"{p} exists: never overwritten (move it aside first)")
    chains, ents, records, cls_of = real_selection(st)
    j, kept, refused = choose(chains, ents, records, cls_of)
    sel = {"plan": PLAN, "ledger": f"pipeline-fix {PHASE_HALF}", "c3r_sha256": st["sha256"], "seed": HALF_SEED,
           "draw": j, "draws_refused": refused, "balance": BALANCE, "chains": len(chains),
           "halves": selection_summary(chains, kept, ents, records), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    sel["sha256"] = selection_sha(sel)
    P.save(p, sel)
    print(f"SELECT draw {j}; sha256 {sel['sha256']}; "
          + "; ".join(f"{s} A {sel['halves']['A']['per_set'][s]['chains']}/{sum(1 for c in chains.values() if c['set'] == s)}"
                      for s in SETS))


def load_selection(st=None):
    """The saved halves, their hash and C3r's state checked. -> the selection."""
    p = selection_path()
    if not p.exists():
        raise SystemExit("no selection: run `half_data select` first")
    sel = json.loads(p.read_text())
    if selection_sha(sel) != sel.get("sha256"):
        raise SystemExit("the selection's content does not match its hash")
    if st is not None and sel["c3r_sha256"] != st["sha256"]:
        raise SystemExit("the selection was made on another C3r state")
    return sel


def half_units(arm, st=None):
    """The units an arm trains on (its half), from the saved selection. -> frozenset."""
    return frozenset(load_selection(st)["halves"][ARMS[arm]["half"]]["units"])


def half_models(st, arm):
    """{fold: (nets, model sha256s, run records)}: an arm's FT_k pair per fold (its seeds in order), each checked as
    `preset_ladder.fold_models` checks R-all's, and its `half` record: arm, base, W seed and selection as declared."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P

    sel = load_selection(st)
    out = {}
    for k in range(FOLDS):
        nm = P.ft_name(k, base=ARMS[arm]["base"])
        nets, recs = zip(*(P.load_run(nm, sd, "best") for sd in ARMS[arm]["seeds"]))
        for r_ in recs:
            R.run_info_check(r_, st)
            hv = r_.get("half") or {}
            if (hv.get("arm"), hv.get("base"), hv.get("w_seed"), hv.get("selection_sha256")) != (
                    arm, ARMS[arm]["base"], half_w_seed(arm, r_["seed"]), sel["sha256"]):
                raise SystemExit(f"{nm}-{r_['seed']}: not a declared arm-{arm} run on today's selection")
            if r_.get("inner") or r_["models"]["best"] != r_["models"]["final"] or r_.get("E") != r_.get("epochs_run"):
                raise SystemExit(f"{nm}-{r_['seed']}: not a read checkpoint at its E")
        out[k] = (list(nets), [r_["model_sha256"]["best"] for r_ in recs], list(recs))
    return out


def same_recipe(run, ref):
    """(Pure.) Problems where a half run's recipe differs from its full-data reference run's (same fold, inner or not,
    same W state): the rate, cap, mask, real-row share and the held units (validation and read: unchanged), and the
    plugin rows. -> [problem]."""
    bad = []
    for f in ("lr", "cap", "masked", "real_frac", "shuffle_real", "real_held_ids", "real_held_units", "held_ids"):
        if run.get(f) != ref.get(f):
            bad.append(f)
    if (run.get("init") or {}).get("sha256") != (ref.get("init") or {}).get("sha256"):
        bad.append("init")
    pr = [i for i in run.get("train_ids", []) if i not in set(run.get("ft_train_ids", []))]
    pf = [i for i in ref.get("train_ids", []) if i not in set(ref.get("ft_train_ids", []))]
    if pr != pf:
        bad.append("plugin train_ids")
    return bad


def half_run_rows(st, run, k, inner, keep):
    """Problems where a half run's real rows differ from the rule: its record's C3r counts equal `rows_for` on its half
    (training units, records and showings per set; held units), and its training units are inside its half and
    inside the full run's. -> [problem]."""
    from learn import full_controls_c3r as R

    _, _, info = R.rows_for("all", k, inner, st, keep=keep)
    got, bad = run.get("c3r") or {}, []
    for f in ("train_units", "held_units", "train_records", "showings", "held_records"):
        if got.get(f) != info.get(f):
            bad.append(f"c3r {f}")
    trained = set((run.get("half") or {}).get("train_units") or [])
    full = run_units(st["entries"], k, inner)
    if not trained:
        bad.append("no training units recorded")
    if trained - keep:
        bad.append("trained outside its half")
    if trained - full:
        bad.append("trained outside the full run's units")
    return bad


def read_bans(st, units, models):
    """(The fold bans for the half models.) Each read part's unit neither trains in its fold's models nor shares a DI
    file or creator with one of their training units. -> [problem]."""
    ent = {e["unit"]: e for e in st["entries"]}
    probs = []
    for k, (_, _, recs) in models.items():
        trained = set().union(*[set((r_.get("half") or {}).get("train_units") or []) for r_ in recs])
        ids = set().union(*[ent[u]["ids"] for u in trained]) if trained else set()
        for ru in units:
            if ru["fold"] != k:
                continue
            if ru["unit"] in trained:
                probs.append(f"{ru['unit']}: trains in its own fold's model")
            if ent[ru["unit"]]["ids"] & ids:
                probs.append(f"{ru['unit']}: shares an identity with fold {k}'s training units")
    return probs


def cmd_answers(_args):
    """The answers (zero renders, CPU; `phase_l6_half`), after the 32 runs: C3r's state, the selection and every
    protected run file unchanged since Step 6's stage 0 (R-rep's against its stage-N answers); each half run on its
    half only, its full reference's recipe (`same_recipe`) and the fold bans; `half-a-xl@-3` and `half-b-xl@-3` on the
    stored `xl@-3` features; their same-input constants and re-centred rows by the ladder's own code. Every output file
    absent before any is written. -> ladder/answers/<row>.json, PF/step6/half/runs.json."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P
    from learn import preset_ladder as L
    from learn import stem_finetune as S6

    require_all()
    s0 = S6.stage0_ok()
    st = R.state()
    if st["sha256"] != s0["c3r_sha256"]:
        raise SystemExit("C3r's state changed since stage 0")
    sel = load_selection(st)
    units = R.read_units(st)
    if S6.runs_manifest() != s0["manifest"]["runs"]:
        raise SystemExit("a protected run file changed, appeared or went since stage 0")
    if S6.feats_manifest(units, "xl@-3") != s0["manifest"]["feats"]["xl@-3"]:
        raise SystemExit("xl@-3's stored features changed since stage 0")
    for r in ("xl@-3", "cen", "rc-xl@-3"):
        if L.file_sha(L.answers_path(r)) != s0["manifest"]["answers"][r]:
            raise SystemExit(f"{r}'s stored answers changed since stage 0")
    S6.answers_check("rep-xl@-3")                      # R-rep's answers made from today's R-rep files
    L.rc_sources_check("rc-rep-xl@-3")
    there = [L.answers_path(r) for r in list(HALF_ROWS) + [f"sic-{r}" for r in HALF_ROWS] + list(RC_HALF_ROWS)
             if L.answers_path(r).exists()]
    if there:
        raise SystemExit(f"{[str(p) for p in there]} exist: never overwritten (move them aside first)")
    od = P.out_dir() / "runs"
    probs, runs, models = [], {}, {}
    for arm, spec in ARMS.items():
        hm = half_models(st, arm)
        models[arm] = hm
        keep = frozenset(sel["halves"][spec["half"]]["units"])
        ref_base = "C3r-all" if arm == "a" else S6.REP_BASES["rep"]
        for k in range(FOLDS):
            for sd in spec["seeds"]:
                for inner in (True, False):
                    nm = P.ft_name(k, inner, P.FT_LR, 300, spec["base"]) if inner else P.ft_name(k, base=spec["base"])
                    rn = P.ft_name(k, inner, P.FT_LR, 300, ref_base) if inner else P.ft_name(k, base=ref_base)
                    run = json.loads((od / f"{nm}-{sd}.json").read_text())
                    ref = json.loads((od / f"{rn}-{sd}.json").read_text())
                    probs += [f"{nm}-{sd}: {b}" for b in same_recipe(run, ref)]
                    probs += [f"{nm}-{sd}: {b}" for b in half_run_rows(st, run, k, inner, keep)]
                    runs[f"{nm}-{sd}"] = {"E": run.get("E"), "epochs_run": run.get("epochs_run"),
                                          "ref": f"{rn}-{sd}", "ref E": ref.get("E"), "minutes": run.get("minutes"),
                                          "at_cap": run.get("at_cap"),
                                          "train_records": (run.get("c3r") or {}).get("train_records"),
                                          "ref train_records": (ref.get("c3r") or {}).get("train_records")}
        probs += [f"arm {arm}: {b}" for b in read_bans(st, units, hm)]
    if probs:
        raise SystemExit(f"the half runs differ from their declared recipe: {probs[:5]} ({len(probs)} problems)")
    for row, arm in HALF_ROWS.items():
        nets = {k: v[0] for k, v in models[arm].items()}
        ans, missing = S6.answer_row(st, units, nets, "xl@-3")
        L.save_answers(row, ans, {"c3r_sha256": st["sha256"], "feats": "xl@-3", "missing": missing,
                                  "models": {str(k): v[1] for k, v in models[arm].items()},
                                  "selection_sha256": sel["sha256"],
                                  "stage0_sha256": L.file_sha(S6.step6_dir() / "stage0.json")})
        print(f"ANSWERS {row}: {sum(len(v) for v in ans.values())} parts, {len(missing)} missing")
    L.cmd_sic(argparse.Namespace(rows=",".join(f"sic-{r}" for r in HALF_ROWS)))
    L.cmd_rc(argparse.Namespace(rows=",".join(RC_HALF_ROWS)))
    out = {"plan": PLAN, "ledger": f"preset-ladder {PHASE_L6_HALF}", "c3r_sha256": st["sha256"],
           "selection_sha256": sel["sha256"], "runs": runs,
           "run_minutes": round(sum(v["minutes"] or 0 for v in runs.values()), 1),
           "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    P.save(half_dir() / "runs.json", out)
    print(f"RUNS saved: {len(runs)} runs, {out['run_minutes']} run-minutes")


def answers_check(row):
    """Refuse when a half row's answers were made from other run files than today's (`preset_ladder.cmd_render`)."""
    from learn import pipeline_fix as P
    from learn import preset_ladder as L

    d = json.loads(L.answers_path(row).read_text())
    spec = ARMS[HALF_ROWS[row]]
    od = P.out_dir() / "runs"
    for k, shas in d["models"].items():
        names = [f"{spec['base']}-k{k}-{sd}-final.pt" for sd in spec["seeds"]]
        if [hashlib.sha256((od / n).read_bytes()).hexdigest() for n in names] != shas:
            raise SystemExit(f"{row}: fold {k}'s models changed since its answers were made")


def value_of(st, name):
    """A row's value function; "a+b" the per-direction geometric mean of the rows (`geo`)."""
    from learn import preset_ladder as L

    parts = name.split("+")
    return L.value_fn(st, parts[0]) if len(parts) == 1 else geo([L.value_fn(st, p) for p in parts])


def cmd_report(_args):
    """The report (zero renders; `phase_l6_half`): every row complete and made from today's answers; H, H_a, H_b and
    the beside rows per set and pooled (`preset_ladder.summarise`); H's adversarial read; the rows saved before
    D_TABLE's cell is read. -> PF/step6/half/report.json."""
    from learn import full_controls_c3r as R
    from learn import pipeline_fix as P
    from learn import preset_ladder as L
    from learn import stem_finetune as S6

    require_all()
    S6.stage0_ok()
    st = R.state()
    load_selection(st)
    units = R.read_units(st)
    complete = {}
    for r in list(HALF_ROWS) + list(RC_HALF_ROWS):
        if L.row_info(r)["kind"] == "rc":
            L.rc_sources_check(r)
        else:
            answers_check(r)
        complete[r] = L.rc_complete(units, r)
    S6.answers_check("rep-xl@-3")
    L.rc_sources_check("rc-rep-xl@-3")
    for r in FULL_RC + FULL_RAW + ("cen",):            # rc_complete refuses a row not rendered from today's answers
        complete[r] = L.rc_complete(units, r)
    band = {u: v["band"] for u, v in L.lends()["units"].items()}
    seen = R.player_seen(st, units)
    out = {"plan": PLAN, "ledger": f"preset-ladder {PHASE_L6_HALF}", "c3r_sha256": st["sha256"],
           "complete": complete, "rows": {}, "pairs": {}, "negatives": {}}
    main = read_parts(units)
    out["parts"] = {"read": len(main), "all": len(units), "left_out": EXCLUDED_READ}
    reads = [(n, ab, main) for n, ab in list(D_ROWS.items()) + list(D_BESIDE.items())]
    reads += [("H with every part", D_ROWS["H"], units),
              ("H without the band's two recordings", D_ROWS["H"], read_parts(units, BAND_BESIDE))]
    for name, (a, b), us in reads:
        got = L.rows_for_pair(st, us, value_of(st, a), value_of(st, b))
        row = L.summarise(got, us, band, seen_player=seen)
        row["directions_read"] = sum(len(v) for v in got.values())
        out["rows"][name], out["pairs"][name] = row, f"{a} - {b}"
        if name == "H":
            out["negatives"][name] = dict(L.negatives(row, row["deciding_sets"]),
                                          leave_one_cluster_out={s: L.loo_range(got, us, s)
                                                                 for s in row["deciding_sets"]})
    out["runs"] = json.loads((half_dir() / "runs.json").read_text())
    out["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    P.save(half_dir() / "report.json", out)            # the rows are saved before the cell is read
    out["outcome"] = d_outcome(out["rows"])
    out["outcome"]["sha256"] = S6.sha_json(out["outcome"])
    P.save(half_dir() / "report.json", out)
    for name, row in out["rows"].items():
        dp = row.get("deciding_pool") or {}
        print(f"{name} ({out['pairs'][name]}): pool {dp.get('mean')} [{dp.get('lo90')}, {dp.get('hi90')}]")
    print("D OUTCOME", json.dumps(out["outcome"]))


COMMANDS = {"select": cmd_select, "answers": cmd_answers, "report": cmd_report}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    args = ap.parse_args(argv)
    return COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
