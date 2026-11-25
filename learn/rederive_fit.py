"""The rebuild's re-derivation: the fit and the builders (`docs/rederive-plan.md` section 6, Unit 3; ledger
`preset-ladder` `phase_scratch_rederive_frozen`). Zero renders.

It builds on the core (`learn/scratch_rederive.py`: `derive`, `compose`, `unfinished`, `input_form` and the declared
rules `FIT`), which it imports and never redefines. The principle: choose the four values (tuning, mutes, tilt,
levels) so that the rebuild, measured by `rebuild_redo`'s own estimators in a stated domain, matches the input.

    $MAIN -m learn.rederive_fit converge --price 2   # amendment 2: the passes timed on 2 (or 3) parts, the wall projected
    $MAIN -m learn.rederive_fit converge             # every iterated candidate, the 47 in in-M, up to 64 passes: the stop
    $MAIN -m learn.rederive_fit bench                # the 12 candidates and today's rule on the 40: the pick
    $MAIN -m learn.rederive_fit build-bench          # the xf-fix guitars: the picked rule handed in-M
    $MAIN -m learn.rederive_fit build-real           # the rf2 guitars: build 2's notes, the picked rule, the true DI
    $MAIN -m learn.rederive_fit freeze               # the rule, the stop, both builds' sha256: the ledger body, printed

`converge`, `bench`, `build-bench` and `build-real` also run in shards (`run_mode`): `--shard k/n` (n <= 8, zero
renders) takes a fixed slice of the parts by key (`shard_keys`: the j-th key goes to shard j mod n) and writes only its
per-part files, each once; `--combine` refuses until every part's file is there, then writes the combined record. With
neither flag one process does every part, then the same combine, so the files are byte-identical either way (no
combined record holds a time). `bench --shard` runs its stage A, and its stage B once every part's stage A is there
(else rerun the shard). `converge --price` also projects the later runs' wall (`price_body`).

**The interface** (Unit 4 reads these; the names are fixed, `BUILD_FIELDS`, `BUILD_PART_FIELDS`, `FREEZE_FIELDS`,
`FREEZE_SECTION_FIELDS`, `HIT_FIELDS`, pinned by a test):
- fit/build-bench.json: plan, renders, row (xf-fix), input, rule, stop, bench_sha256, parts_n, hits,
  identical_to_now, parts; fit/build-real.json: plan, renders, row (fs-refit), build (rf2), input, rule, stop,
  bench_sha256, parts_n, hits, rule_off_is_x ({held, of}), identical_to_x, parts.
- Each `parts[pkey]`: file_sha256 (the sha256 of the guitar's .npy file, `guitar_path(row, pkey)`), audio_sha256
  (`scratch_search.npy_sha` of its float32 samples), values, pass_used, end, reached, identical_to_now (the bench build
  only), identical_to_x.
- The freeze body: plan, renders, rule ({candidate, domain, passes, mutes}), stop, max_passes, fit, choices, converge
  ({sha256, fits, ends, hits}), bench ({sha256, parts, deciding_parts, lowest, ties}), build_bench ({sha256, row,
  parts, hits}), build_real ({sha256, row, build, parts, hits, rule_off_is_x}); each hit {part (a 12-hex tag), set,
  candidate, end, pass_used}. `freeze` prints `{"phase_scratch_rederive_frozen": {"sha256": <frozen.json's>, **body}}`.

**Candidates** (`CANDIDATES`, 12, plus `today`): the comparison domain (`unfinished`: `denoise_above(synthesise_redo(V))
[:n]`; `measured`: that after `song_bank.measure`, rounded to float32 as `in-M` is; `finished`: `compose(V)` with the
part's finish, rounded to float32 as `in-F` is), the passes (`one` correction, or `iterated`) and the mutes (`as-now`:
every drop the input shows is a mute; `veto`: in time order a drop is kept only if the rebuild has no mute of its own
within 30 ms). They are numbered in the declared "simpler" total order (`simpler_key`): today's rule first; then fewer
passes; then the domain (unfinished, measured, finished); then mutes as now before the veto.

**A pass** (`fit`). Pass 0 is today's rule, R = `derive(input)`. Pass k rebuilds pass k-1's values V in the domain (y),
measures input and y with the same estimators and adds the difference:
- tuning: `global_tuning_cents(input) - global_tuning_cents(y)`, wrapped to +-50 cents;
- tilt: `sustain_tilt`'s median before its clamp (input less y), both against the plain synthesis with V's tuning and
  mutes, as `derive` builds it;
- levels: `oracle_gains(input) - oracle_gains(y)` per onset group, both against the plain synthesis with V's tilt;
- mutes: each drop the input shows (`mute_times(input)`, fixed: R's mutes) carries a time; a drop whose mute was in
  the rebuild moves by the input's drop time less the rebuild's nearest drop within 30 ms (none: it stays). The mute
  rule then says which drops are mutes in pass k (as now: all; the veto: `veto_members`).
Tuning and tilt take a secant step from the second pass on (`secant`); levels and mute times the plain step.

**Repeats, cycles, the stop** (`repeats`, `cycle_match`, `pass_used`, `safety_stop`): as `FIT` declares them. A pass
repeats when against its predecessor the tuning moved under 0.05 cents, the mute list is identical, every level moved
under 0.01 dB and the tilt under 0.027 dB/s; the fit stops there and uses that pass. A pass that matches (within the
same tolerances) any earlier pass but its predecessor stops the fit: the pass used is the cycle's member with the
lowest residual, a tie the earliest. `converge` sets the stop: the largest pass count among the fits that repeated;
every fit that reaches it is listed, its pass used the lowest-residual pass at or before the stop. The stop applies to
`bench`, `build-bench` and `build-real` (amendment 5); the real fits that reach it are listed too.

**The pick** (`pick`): `note_rebuild.logmel_distance` from each candidate's finished guitar to X, in in-M, on the 40;
the lowest pooled mean (`scratch_notes.set_rows`' BKS+GOAT pool); every candidate whose per-part paired difference
from it has an interval spanning zero ties with it; the simplest of the lowest and its ties is picked.

**Implementer's choices** (`CHOICES`), recorded for review because the declaration does not spell them out: the
residual, the mute times' correction, the clamps, the secant's fallback, the levels' centring, pass 0's place and the
order inside a pass.

Every command refuses unless this checkout runs main's code (this module and the core's `CODE_FILES`) and keys, and
main holds the declaration and `phase_scratch_rederive_ladder` with ladder.json's sha256. Each file is written once.
The pure parts (the candidates and their order, `secant`, `repeats`, `cycle_match`, `pass_used`, `safety_stop`,
`pick`, `freeze_body`) run on the light CI runner (no numpy); the fit itself on a made-up bank (numpy, skipped
elsewhere): tests/test_rederive_fit.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import statistics
import time

from learn import note_rebuild as NR
from learn import note_transcribe as NT
from learn import scratch_exact as SE
from learn import scratch_rederive as RD
from learn import scratch_search as S

FIT = RD.FIT
PLAN = RD.PLAN
DOMAINS, PASSES, MUTE_RULES = FIT["domains"], FIT["passes"], FIT["mutes"]
TODAY = "today"                          # today's rule: R = derive(input), no pass
MAX_PASSES = FIT["max_passes"]           # 64: converge's bound
VETO_S = FIT["mute_veto_s"]              # 0.030 (MUTE_FADE_S): the veto's window and the mute times' match window
TOL_TUNING = FIT["repeat_tuning_cents"]  # 0.05
TOL_LEVEL = FIT["repeat_level_db"]       # 0.01
TOL_TILT = FIT["repeat_tilt_db_s"]       # 0.027
TUNING_LIMIT = 50.0                      # global_tuning_cents' own range
TILT_LIMIT = NR.TILT_MAX_DB_S            # 12: the rule's own tilt clamp
LEVEL_LIMIT = NR.ORACLE_CLAMP_DB         # 20: oracle_gains' own clamp
PRICE_PARTS = (2, 3)                     # amendment 2: the pricing step's part counts
OWN_FILES = ("learn/rederive_fit.py",)
CODE_FILES = OWN_FILES + RD.CODE_FILES
FIX_ROW, REAL_ROW = RD.FIX_ROW, RD.REAL_ROW
BUILDS = {"bench": FIX_ROW, "real": REAL_ROW}

CHOICES = {
    "residual": "note_rebuild.logmel_distance from the input to the rebuild in the candidate's domain (the input is "
                "the side whose playing frames count); a non-finite distance counts as the largest",
    "mute_times": "the mutes are the input's drops (mute_times(input)), each with a time that takes the measured "
                  "difference: the input's drop less the rebuild's nearest drop within 30 ms, none: unchanged; only "
                  "drops that were mutes in the rebuild move, each held within 30 ms of its drop (the window that "
                  "makes it the same mute; an inert mute, one that cuts nothing, would otherwise drift); the mute "
                  "rule says which drops are mutes",
    "clamps": "tuning held within +-50 cents (global_tuning_cents' range), tilt within +-12 dB/s (the rule's own clamp), "
              "each level within +-20 dB (oracle_gains' own clamp)",
    "tilt_measure": "sustain_tilt's median before its clamp (raw_db_s); 0 when it applies to no part (under 3 isolated "
                    "groups, the same for input and rebuild)",
    "levels_centred": "after each step the levels are centred on the median of the usable groups (oracle_gains' own "
                      "rule), unusable groups 0 dB, as derive's levels are",
    "secant": "from the second pass on, value + difference / slope, the slope the fall in the difference per unit of "
              "value over the last two passes; a change under the element's repeat tolerance (its response is not "
              "measurable there), a non-finite one, or a slope not above zero: the plain step",
    "pass_0": "pass 0 is today's rule (R); a repeat is checked against it, but it is never a cycle member nor a pass "
              "used at the stop (passes 1 to the stop)",
    "order": "every element of pass k is measured on the rebuild of pass k-1 (one rebuild per pass); the veto's "
             "rebuilds use pass k-1's tuning, tilt and levels with the mute times of pass k",
    "lowest_mean": "the pooled BKS+GOAT mean of set_rows on the 40; an equal mean goes to the simpler",
}


# --- the candidates and their order (pure) --------------------------------------------------------------------------------

def candidate_id(domain, passes, mutes):
    if domain not in DOMAINS or passes not in PASSES or mutes not in MUTE_RULES:
        raise ValueError((domain, passes, mutes))
    return f"{domain}/{passes}/{mutes}"


def candidate(cid):
    """(Pure.) {domain, passes, mutes} of a candidate id; None for today's rule."""
    if cid == TODAY:
        return None
    parts = cid.split("/") if isinstance(cid, str) else ()
    if len(parts) != 3:
        raise ValueError(cid)
    d, p, m = parts
    candidate_id(d, p, m)
    return {"domain": d, "passes": p, "mutes": m}


def simpler_key(cid):
    """(Pure.) The declared "simpler" total order: today's rule first; then fewer passes; then the domain (unfinished,
    measured, finished); then mutes as now before the veto."""
    c = candidate(cid)
    if c is None:
        return (0, 0, 0, 0)
    return (1, PASSES.index(c["passes"]), DOMAINS.index(c["domain"]), MUTE_RULES.index(c["mutes"]))


CANDIDATES = tuple(sorted((candidate_id(d, p, m) for d in DOMAINS for p in PASSES for m in MUTE_RULES), key=simpler_key))
ORDER = (TODAY,) + CANDIDATES            # every rule the bench reads, simplest first
ITERATED = tuple(c for c in CANDIDATES if candidate(c)["passes"] == "iterated")


def iterated_of(cid):
    """(Pure.) The iterated candidate whose trace holds this candidate's values (pass 1 of it for a one-pass one)."""
    c = candidate(cid)
    return candidate_id(c["domain"], "iterated", c["mutes"])


def fit_guard():
    """Refuse unless the candidates are the declared 12 in a total order, the tolerances are FIT's and the limits the
    estimators' own."""
    if len(CANDIDATES) != FIT["candidates"] or len(set(map(simpler_key, ORDER))) != len(ORDER):
        raise SystemExit("the candidates are not the declared 12 in a total order")
    if (TOL_TUNING, TOL_LEVEL, TOL_TILT, VETO_S, MAX_PASSES) != (0.05, 0.01, 0.027, NR.MUTE_FADE_S, 64):
        raise SystemExit("the fit's tolerances are not the declared ones")
    if len(ITERATED) != 6:
        raise SystemExit("the iterated candidates are not six")


# --- the update rules (pure) ----------------------------------------------------------------------------------------------

def clamp(v, lim):
    return max(-lim, min(lim, v))


def wrap_cents(d):
    """(Pure.) A tuning difference wrapped to [-50, 50) cents (the tuning is circular over a semitone)."""
    return ((d + 50.0) % 100.0) - 50.0


def secant(v1, v0, d1, d0, resolution):
    """(Pure.) The next value from the last two passes: v1, v0 the values, d1, d0 the differences measured at them
    (input less rebuild). The slope is the fall in the difference per unit of value. A change under `resolution` (the
    element's repeat tolerance: below it the response is not measurable, e.g. under half of Bank.note's 0.1-cent
    rounding), a non-finite one, or a slope not above zero, takes the plain step v1 + d1. -> (value, "secant" or
    "plain")."""
    dv, dd = v1 - v0, d0 - d1
    if not math.isfinite(dv) or not math.isfinite(dd) or abs(dv) < resolution:
        return v1 + d1, "plain"
    s = dd / dv
    if not (math.isfinite(s) and s > 0):
        return v1 + d1, "plain"
    return v1 + d1 / s, "secant"


def repeats(a, b):
    """(Pure.) FIT's "repeats", also the cycle rule's "matches": tuning moved under 0.05 cents, the mute list identical,
    every level moved under 0.01 dB, the tilt under 0.027 dB/s."""
    if len(a["levels"]) != len(b["levels"]):
        raise ValueError("the two value sets have different onset groups")
    return (abs(a["tuning"] - b["tuning"]) < TOL_TUNING
            and [float(t) for t in a["mutes"]] == [float(t) for t in b["mutes"]]
            and all(abs(x - y) < TOL_LEVEL for x, y in zip(a["levels"], b["levels"]))
            and abs(a["tilt"] - b["tilt"]) < TOL_TILT)


def cycle_match(values, k):
    """(Pure.) The earliest pass j in 1..k-2 that pass k matches within the repeat tolerances, or None. values: the
    passes' values, index = pass (0 today's rule, never matched)."""
    for j in range(1, k - 1):
        if repeats(values[k], values[j]):
            return j
    return None


def _lowest(trace, passes):
    """(Pure.) The pass with the lowest residual among `passes`, a tie the earliest; a non-finite residual counts as
    the largest; a pass whose rebuild was never measured refuses."""
    def r(k):
        x = trace[k].get("residual")
        if x is None:
            if trace[k].get("residual_nonfinite"):
                return math.inf
            raise ValueError(f"pass {k} has no residual")
        return x
    return min(passes, key=lambda k: (r(k), k))


def reached(end, stop):
    """(Pure.) Whether a fit reaches the stop: it did not repeat or cycle at or before it (a one-pass candidate or
    today's rule never does)."""
    if end["kind"] in (TODAY, "one"):
        return False
    return not (end["kind"] in ("repeat", "cycle") and end["at"] <= stop)


def pass_used(trace, end, stop):
    """(Pure.) The pass a fit uses under the stop: today's rule 0; a one-pass candidate 1; a fit that repeated at or
    before the stop, that pass; one that cycled at or before it, the cycle's lowest-residual member (a tie the earliest);
    otherwise the lowest-residual pass in 1..stop. trace: [{"pass", "values", "residual"}], index = pass."""
    kind, at = end["kind"], end["at"]
    if kind == TODAY:
        return 0
    if kind == "one":
        return 1
    if not isinstance(stop, int) or stop < 1:
        raise ValueError(f"the stop {stop!r} is not a pass count")
    if kind == "repeat" and at <= stop:
        return at
    if kind == "cycle" and at <= stop:
        return _lowest(trace, range(end["matches"], at))
    if len(trace) <= stop:
        raise ValueError(f"the trace ends at pass {len(trace) - 1}, before the stop {stop}")
    return _lowest(trace, range(1, stop + 1))


def safety_stop(ends):
    """(Pure.) converge's stop from its fits' ends ({fit: end}): the largest pass count among the fits that repeated,
    and every fit that reaches it (sorted). No fit repeated: (None, all). -> (stop, [fit])."""
    at = [e["at"] for e in ends.values() if e["kind"] == "repeat"]
    if not at:
        return None, sorted(ends)
    stop = max(at)
    return stop, sorted(f for f, e in ends.items() if reached(e, stop))


def values_for(traces, cid, stop):
    """(Pure.) A candidate's values on one part from converge's traces ({iterated cid: {"trace", "end"}}): today's
    rule pass 0 (the same in every trace), a one-pass candidate pass 1 of its iterated twin, an iterated one
    `pass_used` under the stop. -> (values json, pass used, reached the stop)."""
    if cid == TODAY:
        zero = {json.dumps(t["trace"][0]["values"], sort_keys=True) for t in traces.values()}
        if len(zero) != 1:
            raise ValueError("the traces start from different values: today's rule differs")
        first = next(iter(traces.values()))
        return first["trace"][0]["values"], 0, False
    t = traces[iterated_of(cid)]
    if candidate(cid)["passes"] == "one":
        if len(t["trace"]) < 2:
            raise ValueError("the trace has no pass 1")
        return t["trace"][1]["values"], 1, False
    k = pass_used(t["trace"], t["end"], stop)
    return t["trace"][k]["values"], k, reached(t["end"], stop)


# --- the pick (pure) ------------------------------------------------------------------------------------------------------

def pick(dist, interval, order=ORDER):
    """(Pure.) The bench's pick. dist: {cid: {pkey: distance to X}} (the parts the interval reads); interval({pkey:
    value}) -> {mean, lo90, hi90} (set_rows' BKS+GOAT pool on the 40). The lowest pooled mean (an equal mean: the
    simpler); each other candidate's per-part paired difference from it, a tie when its interval spans zero; the
    simplest of the lowest and its ties. An unusable interval refuses. -> dict."""
    means = {}
    for c in order:
        iv = interval(dist[c])
        if not RD.iv_ok(iv):
            raise SystemExit(f"{c}: no usable interval of its distances: to the user")
        means[c] = float(iv["mean"])
    low = min(order, key=lambda c: (means[c], simpler_key(c)))
    diffs = {}
    for c in order:
        if c == low:
            continue
        if set(dist[c]) != set(dist[low]):
            raise SystemExit(f"{c} and {low} were read on different parts")
        iv = interval({k: dist[c][k] - dist[low][k] for k in dist[low]})
        if not RD.iv_ok(iv):
            raise SystemExit(f"{c} less {low}: no usable interval: to the user")
        diffs[c] = {"mean": iv["mean"], "lo90": iv["lo90"], "hi90": iv["hi90"], "tie": RD.spans_zero(iv)}
    pool = [low] + [c for c in order if c in diffs and diffs[c]["tie"]]
    chosen = min(pool, key=simpler_key)
    return {"candidate": chosen, "lowest": low, "ties": [c for c in pool if c != low], "means": means,
            "less_lowest": diffs, "order": list(order)}


# --- the ledger body (pure) -----------------------------------------------------------------------------------------------

def part_tag(pk):
    """(Pure.) A part's tag for the ledger: the first 12 hex digits of its key's sha256 (git holds no part keys)."""
    return hashlib.sha256(pk.encode()).hexdigest()[:12]


def _hits_public(hits, sets_of):
    return [{"part": part_tag(h["part"]), "set": sets_of.get(h["part"]), "candidate": h["candidate"],
             "end": h["end"], "pass_used": h["pass_used"]} for h in hits]


def freeze_body(conv, bench, builds, shas):
    """(Pure.) `phase_scratch_rederive_frozen`'s body: the rule, the stop, both lists of fits that reached it (part
    tags only), the counts, and the sha256 of converge's, the bench's and both builds' records. shas: {converge, bench,
    build_bench, build_real}."""
    rule = bench["pick"]["candidate"]
    if conv["stop"] != bench["stop"] or any(b["stop"] != conv["stop"] for b in builds.values()):
        raise SystemExit("converge, the bench and the builds do not share the stop")
    if any(b["rule"] != rule for b in builds.values()):
        raise SystemExit("the builds were not made with the bench's pick")
    if bench["converge_sha256"] != shas["converge"] or any(b["bench_sha256"] != shas["bench"]
                                                            for b in builds.values()):
        raise SystemExit("the records do not chain: converge -> bench -> builds")
    sets_of = {**bench.get("sets", {})}
    return {"plan": PLAN, "renders": 0, "rule": {"candidate": rule, **(candidate(rule) or {"today": True})},
            "stop": conv["stop"], "max_passes": MAX_PASSES, "fit": {k: FIT[k] for k in sorted(FIT)},
            "choices": dict(CHOICES),
            "converge": {"sha256": shas["converge"], "fits": conv["fits"], "ends": conv["ends"],
                         "hits": _hits_public(conv["hits"], sets_of)},
            "bench": {"sha256": shas["bench"], "parts": bench["parts_n"], "deciding_parts": bench["deciding_n"],
                      "lowest": bench["pick"]["lowest"], "ties": bench["pick"]["ties"]},
            "build_bench": {"sha256": shas["build_bench"], "row": FIX_ROW, "parts": builds["bench"]["parts_n"],
                            "hits": _hits_public(builds["bench"]["hits"], sets_of)},
            "build_real": {"sha256": shas["build_real"], "row": REAL_ROW, "build": RD.REAL_BUILD,
                           "parts": builds["real"]["parts_n"], "hits": _hits_public(builds["real"]["hits"], sets_of),
                           "rule_off_is_x": builds["real"]["rule_off_is_x"]}}


# --- paths ------------------------------------------------------------------------------------------------------------------

def fit_dir():
    return RD.rederive_dir() / "fit"


def price_path():
    return fit_dir() / "price.json"


def trace_path(pk):
    return fit_dir() / "converge" / f"{SE._f(pk)}.json"


def converge_path():
    return fit_dir() / "converge.json"


def bench_part_path(pk):
    return fit_dir() / "bench" / f"{SE._f(pk)}.json"


def bench_path():
    return fit_dir() / "bench.json"


def beside_part_path(pk):
    return fit_dir() / "beside" / f"{SE._f(pk)}.json"


def build_record_path(which):
    if which not in BUILDS:
        raise ValueError(which)
    return fit_dir() / f"build-{which}.json"


def frozen_path():
    return fit_dir() / "frozen.json"


def guitar_path(row, pk):
    """The builds' guitars, beside the ladder's: dry/xf-fix/ and dry/fs-refit/ under PF/fs/rederive/."""
    if row not in BUILDS.values():
        raise ValueError(row)
    return RD.rederive_dir() / "dry" / row / f"{SE._f(pk)}.npy"


# --- the guards ---------------------------------------------------------------------------------------------------------------

def own_identity():
    return {f: SE._git("diff", "--quiet", "origin/main", "--", f).returncode == 0 for f in OWN_FILES}


def require_fit(*phases):
    """Refuse unless the core's guard holds (main's code and keys, the declaration) with the ladder's hash on main,
    this module equals main's, and the fit's rules are the declared ones. -> main's `preset-ladder` entry."""
    m = RD.require_rederive(RD.PHASE_LADDER, *phases)
    bad = [f for f, ok in own_identity().items() if not ok]
    if bad:
        raise SystemExit(f"this checkout's {bad} differ from main's: run from merged code")
    fit_guard()
    return m


def _finite(x):
    return float(x) if x is not None and math.isfinite(x) else None


def _save_once(path, obj):
    from learn import pipeline_fix as P

    NT.never_overwrite(path)
    P.save(path, obj)
    return S.file_sha(path)


def _load_checked(path, sha=None, what=None):
    if not pathlib.Path(path).exists():
        raise SystemExit(f"no {pathlib.Path(path).name} (run `{what}` first)")
    if sha is not None and S.file_sha(path) != sha:
        raise SystemExit(f"{pathlib.Path(path).name} changed since its record")
    return json.loads(pathlib.Path(path).read_text())


# --- a part (numpy) ------------------------------------------------------------------------------------------------------------

class Part:
    """One part's world: the notes and length, the bank, the ring variant, the loudness option, the finish, the
    measure step (None: `song_bank.measure`), and on the bench the true DI, X, T and the in-M input."""

    def __init__(self, notes, n, bank, ring, loud=None, finish=None, measure=None, rate=NR.SR, key=None, set_=None,
                 di=None, X=None, T=None, u=None, record=None):
        self.notes, self.n, self.bank, self.ring, self.loud = notes, n, bank, ring, loud
        self.finish, self.measure, self.rate = finish, measure, rate
        self.key, self.set, self.di, self.X, self.T, self.u, self.record = key, set_, di, X, T, u, record
        self._forms = {}

    def form(self, kind):
        """An input form of X from T (`scratch_rederive.input_form`), checked against the ladder's record when given."""
        if kind not in self._forms:
            raw = RD.unfinished(self.notes, self.n, self.bank, self.ring, self.T, self.loud, self.rate)
            y = RD.input_form(kind, self.notes, self.n, self.bank, self.ring, self.T, self.di, self.finish, self.loud,
                              self.measure, raw, self.rate)
            if self.record is not None and S.npy_sha(y) != self.record["inputs"][kind]["input_sha256"]:
                raise SystemExit(f"{self.key}: {kind} is not the ladder's")
            self._forms[kind] = y
        return self._forms[kind]


def usable_groups(p):
    """`oracle_gains`' usable groups (onset inside the window, a level span of MIN_SPAN_S or more). `note_rebuild`
    has no function for the rule (it is inline in `oracle_gains` and `level_gains`), so it is restated from
    `onset_groups` and `group_spans`; tests/test_rederive_fit.py pins it to `oracle_gains`' zeros."""
    groups = NR.onset_groups(p.notes)
    spans = NR.group_spans(p.notes, groups, p.n, p.rate)
    return [p.notes[g[0]]["on"] >= 0 and b - a >= NR.MIN_SPAN_S * p.rate for g, (a, b) in zip(groups, spans)]


def centred(levels, ok):
    """Levels centred on the usable groups' median, each within +-LEVEL_LIMIT, unusable 0 dB: `oracle_gains`' own
    step (`note_rebuild._span_gains`), called, not copied."""
    return NR._span_gains(list(levels), list(ok), LEVEL_LIMIT)


def rebuild_in(p, V, domain):
    """The rebuild of values V in a comparison domain: unfinished, measured (as in-M is built) or finished (as in-F)."""
    if domain == "unfinished":
        return RD.unfinished(p.notes, p.n, p.bank, p.ring, V, p.loud, p.rate)
    if domain == "measured":
        raw = RD.unfinished(p.notes, p.n, p.bank, p.ring, V, p.loud, p.rate)
        return RD.input_form("in-M", p.notes, p.n, p.bank, p.ring, V, None, measure=p.measure, raw=raw, rate=p.rate)
    if domain == "finished":
        return RD.input_form("in-F", p.notes, p.n, p.bank, p.ring, V, None, p.finish, p.loud, rate=p.rate)
    raise ValueError(domain)


def guitar(p, V):
    """The finished guitar of values V (`compose`, as `rebuild_redo` ends), as float32 (the file's samples)."""
    import numpy as np

    y, _ = RD.compose(p.notes, p.n, p.bank, p.ring, p.finish, V, p.loud, p.rate)
    return np.asarray(y, np.float32)


def residual(u, y):
    """CHOICES["residual"]: the logmel distance from the input to the rebuild in the domain."""
    import numpy as np

    return float(NR.logmel_distance(np.asarray(u, np.float64), np.asarray(y, np.float64)))


def _tilt_raw(p, plain0, x):
    _, rep = NR.sustain_tilt(p.notes, plain0, x, p.rate)
    return float(rep["raw_db_s"]) if rep.get("applied") else 0.0


def differences(p, V, u, y, tuning_u=None):
    """The measured differences, input less rebuild, with `rebuild_redo`'s estimators against the plain syntheses
    `derive` builds from V. -> {tuning, tilt, levels, y_drops}."""
    plain0, _ = RD._synth(p.notes, p.n, p.bank, p.ring, V["tuning"], V["mutes"], 0.0, None, p.loud, p.rate, last=False)
    plain, _ = RD._synth(p.notes, p.n, p.bank, p.ring, V["tuning"], V["mutes"], V["tilt"], None, p.loud, p.rate,
                         last=False)
    plain0, plain = plain0[:p.n], plain[:p.n]
    tu = NR.global_tuning_cents(u, p.rate) if tuning_u is None else tuning_u
    return {"tuning": wrap_cents(tu - NR.global_tuning_cents(y, p.rate)),
            "tilt": _tilt_raw(p, plain0, u) - _tilt_raw(p, plain0, y),
            "levels": [a - b for a, b in zip(NR.oracle_gains(p.notes, plain, u, p.rate),
                                              NR.oracle_gains(p.notes, plain, y, p.rate))],
            "y_drops": NR.mute_times(y, p.rate)}


def _nearest(t, xs, tol=VETO_S):
    best = None
    for x in xs:
        if abs(x - t) <= tol + 1e-12 and (best is None or abs(x - t) < abs(best - t)):
            best = x
    return best


def mute_offsets(drops, off, member, y_drops):
    """CHOICES["mute_times"]: each drop that was a mute moves by its time less the rebuild's nearest drop within 30
    ms (none: unchanged), held within 30 ms of its drop. -> new offsets."""
    out = list(off)
    for i, t in enumerate(drops):
        if member[i]:
            near = _nearest(t, y_drops)
            if near is not None:
                out[i] = float(clamp(off[i] + (t - near), VETO_S))
    return out


def mute_list(drops, off, member):
    return sorted(float(t + o) for t, o, k in zip(drops, off, member) if k)


def veto_members(p, drops, off, V, domain):
    """The mute veto: in time order, a drop is kept only if the rebuild (V's tuning, tilt and levels, the mutes kept so
    far at their times) has no mute of its own within 30 ms of it. -> [member per drop]."""
    member = [False] * len(drops)
    order = sorted(range(len(drops)), key=lambda i: (drops[i], i))
    if not order:
        return member
    own = NR.mute_times(rebuild_in(p, dict(V, mutes=[]), domain), p.rate)
    for idx, i in enumerate(order):
        if _nearest(drops[i], own) is not None:
            continue
        member[i] = True
        if idx < len(order) - 1:
            own = NR.mute_times(rebuild_in(p, dict(V, mutes=mute_list(drops, off, member)), domain), p.rate)
    return member


def fit(p, u, cid, max_passes=MAX_PASSES, log=None):
    """One candidate on one part: today's rule R = derive(u), then the passes (module docstring) up to `max_passes`
    (1 for a one-pass candidate). -> {"candidate", "values" (the pass used's), "pass_used", "end", "trace",
    "reached"}. trace[k]: pass k's values (json), its residual (None until its rebuild is measured), its steps, its
    mute offsets and members."""
    c = candidate(cid)
    R, _ = RD.derive(p.notes, p.n, p.bank, u, p.ring, p.loud, None, p.rate)
    R = RD.values_json(R)
    drops = list(R["mutes"])
    off, member = [0.0] * len(drops), [True] * len(drops)
    trace = [{"pass": 0, "values": R, "residual": None, "steps": None, "mute_offsets_s": list(off),
              "members": list(member)}]
    if c is None:
        return {"candidate": cid, "values": R, "pass_used": 0, "end": {"kind": TODAY, "at": 0}, "trace": trace,
                "reached": False}
    limit = 1 if c["passes"] == "one" else int(max_passes)
    if limit < 1:
        raise ValueError(f"max_passes {max_passes!r}")
    ok = usable_groups(p)
    tuning_u = NR.global_tuning_cents(u, p.rate)
    V, D, end = [R], [], None
    for k in range(1, limit + 1):
        prev = V[-1]
        y = rebuild_in(p, prev, c["domain"])
        r = residual(u, y)
        trace[-1]["residual"] = _finite(r)
        trace[-1]["residual_nonfinite"] = _finite(r) is None
        d = differences(p, prev, u, y, tuning_u)
        D.append(d)
        nxt, steps = {}, {}
        for e, lim, res in (("tuning", TUNING_LIMIT, TOL_TUNING), ("tilt", TILT_LIMIT, TOL_TILT)):
            if k >= 2:
                v, how = secant(prev[e], V[-2][e], d[e], D[-2][e], res)
            else:
                v, how = prev[e] + d[e], "plain"
            nxt[e], steps[e] = float(clamp(v, lim)), how
        nxt["levels"] = centred([a + b for a, b in zip(prev["levels"], d["levels"])], ok)
        off = mute_offsets(drops, off, member, d["y_drops"])
        if c["mutes"] == "as-now":
            member = [True] * len(drops)
        else:
            member = veto_members(p, drops, off, dict(prev), c["domain"])
        nxt["mutes"] = mute_list(drops, off, member)
        nxt = RD.values_json(nxt)
        V.append(nxt)
        trace.append({"pass": k, "values": nxt, "residual": None, "steps": steps, "mute_offsets_s": list(off),
                      "members": list(member)})
        if log:
            log(f"  {cid} pass {k}: residual of pass {k - 1} {r:.4f}")
        if repeats(nxt, prev):
            end = {"kind": "repeat", "at": k}
            break
        j = cycle_match(V, k)
        if j is not None:
            end = {"kind": "cycle", "at": k, "matches": j}
            break
    if end is None:
        end = {"kind": "one" if c["passes"] == "one" else "limit", "at": limit}
    if end["kind"] == "limit":
        r = residual(u, rebuild_in(p, V[-1], c["domain"]))
        trace[-1]["residual"] = _finite(r)
        trace[-1]["residual_nonfinite"] = _finite(r) is None
    k = pass_used(trace, end, limit)
    return {"candidate": cid, "values": trace[k]["values"], "pass_used": k, "end": end, "trace": trace,
            "reached": reached(end, limit)}


# --- the parts (real data) -------------------------------------------------------------------------------------------------

def bench_parts(m, keys=None):
    """The 47 bench parts as `scratch_rederive ladder` made them, each checked against main's ladder: build 2's notes
    after its fixes, the true DI, X, T (equal to the ladder's record) and the in-M input (its sha256 the ladder's).
    keys: only these parts. -> [Part] in key order (a generator)."""
    import numpy as np

    from learn import note_fixes as NF

    lad = NT.require_file_hash(m, RD.PHASE_LADDER, RD.ladder_path())
    if not lad.get("proofs_hold"):
        raise SystemExit("the ladder's proofs did not hold")
    b2 = SE.bank_build(m)
    xb = SE.require_xbuild(m)
    fixes, ring, loud = lad["fixes"], lad["ring_variant"], lad["loud_gamma"]
    if (b2["fixes"], b2["ring_variant"], b2.get("loud_gamma")) != (fixes, ring, loud):
        raise SystemExit("the ladder was not made with build 2's rule")
    excl, _, _, _ = NT._dev_context()
    bank = NR.Bank(NR.load_notes_doc(), excl=excl)
    todo = NT.build_todo(NT.install_pair(NT.load_manifest()), NT.ear_items_file(RD.BANK_BUILD))
    parts = sorted((t for t in todo if t[0] == "part"), key=lambda t: t[1])
    if sorted(k for _, k, *_ in parts) != sorted(lad["parts"]):
        raise SystemExit("the parts are not the ladder's")
    for _kind, key, info, rec, di, finish in parts:
        if keys is not None and key not in keys:
            continue
        r = _load_checked(RD.part_path(key), lad["parts"][key]["record_sha256"], "scratch_rederive ladder")
        di = np.asarray(di, np.float64)
        if S.npy_sha(di) != xb["parts"][key]["guitars"]["xn-swap"]["sha256"]:
            raise SystemExit(f"{key}: the DI is not the exact-notes build's true DI")
        X32 = NT.load_dry(RD.BANK_ARM, key, b2)
        if S.npy_sha(X32) != b2["parts"][key]["arms"][RD.BANK_ARM]["sha256"]:
            raise SystemExit(f"{key}: X is not build 2's")
        notes, _ = NT.timed_notes(rec, di)
        exact, _ = NF.apply_fixes(notes, fixes, di)
        if len(exact) != r["notes"] or len(X32) != r["n"] or len(di) != r["n"]:
            raise SystemExit(f"{key}: the notes or the length are not the ladder's")
        p = Part(exact, r["n"], bank, ring, loud, finish, None, NR.SR, key, info["set"], di,
                 np.asarray(X32, np.float64), None, None, r)
        T, _ = RD.derive(exact, p.n, bank, di, ring, loud)
        if RD.values_json(T) != r["T"]:
            raise SystemExit(f"{key}: T is not the ladder's")
        p.T = T
        p.u = p.form(RD.DECIDING_INPUT)
        p.x_sha = b2["parts"][key]["arms"][RD.BANK_ARM]["sha256"]
        p.now_sha = r["files"][RD.NOW_ROW]["audio_sha256"]
        yield p


def _main_parts(m):
    lad = NT.require_file_hash(m, RD.PHASE_LADDER, RD.ladder_path())
    return sorted(lad["parts"])


# --- shards, run modes and the record formats (pure) -----------------------------------------------------------------------

SHARD_MAX = 8                            # zero renders: at most the machine's 8 cores (the orchestrator's run mode)
LATER_FITS = {"bench in-U and in-F": 2, "build-bench": 1, "build-real": 1}   # the picked rule's fits per part
LATER_COMPOSES = 23                      # per part: the bench's 13 rules, 4 beside guitars, 1 + 2 build guitars, and
#                                          today's 3 derives (beside twice, build-real's rule off), one compose each

# The interface other units read (Unit 4, `learn/rederive_rows.py`, is coded against these names; never renamed).
# `file_sha256` is the sha256 of the guitar's .npy file as written; `audio_sha256` is `scratch_search.npy_sha` of its
# samples (float32), the same for a file and the array it holds.
BUILD_PART_FIELDS = {    # build-<which>.json's "parts"[pkey]
    "bench": ("file_sha256", "audio_sha256", "values", "pass_used", "end", "reached", "identical_to_now",
              "identical_to_x"),
    "real": ("file_sha256", "audio_sha256", "values", "pass_used", "end", "reached", "identical_to_x"),
}
BUILD_FIELDS = {         # build-<which>.json (fit/build-bench.json, fit/build-real.json)
    "bench": ("plan", "renders", "row", "input", "rule", "stop", "bench_sha256", "parts_n", "hits", "identical_to_now",
              "parts"),
    "real": ("plan", "renders", "row", "build", "input", "rule", "stop", "bench_sha256", "parts_n", "hits",
             "rule_off_is_x", "identical_to_x", "parts"),
}
FREEZE_FIELDS = ("plan", "renders", "rule", "stop", "max_passes", "fit", "choices", "converge", "bench", "build_bench",
                 "build_real")      # freeze_body; `freeze` prints {PHASE_FROZEN: {"sha256": frozen.json's, **body}}
FREEZE_SECTION_FIELDS = {
    "rule": ("candidate", "domain", "passes", "mutes"),           # today's rule: ("candidate", "today")
    "converge": ("sha256", "fits", "ends", "hits"),
    "bench": ("sha256", "parts", "deciding_parts", "lowest", "ties"),
    "build_bench": ("sha256", "row", "parts", "hits"),
    "build_real": ("sha256", "row", "build", "parts", "hits", "rule_off_is_x"),
}
HIT_FIELDS = ("part", "set", "candidate", "end", "pass_used")    # each hit in the body: "part" a part tag, not a key


def shard_arg(s):
    """`--shard k/n`: 0 <= k < n <= SHARD_MAX."""
    try:
        k, n = (int(x) for x in s.split("/"))
    except ValueError:
        raise argparse.ArgumentTypeError("k/n") from None
    if not 0 <= k < n <= SHARD_MAX:
        raise argparse.ArgumentTypeError(f"k/n with 0 <= k < n <= {SHARD_MAX}")
    return k, n


def shard_keys(keys, shard):
    """(Pure.) A shard's fixed slice of the parts: the j-th key in key order goes to shard j mod n; None: every part."""
    keys = sorted(keys)
    if shard is None:
        return keys
    k, n = shard
    return [x for j, x in enumerate(keys) if j % n == k]


def run_mode(args, price_ok=False):
    """(Pure.) One of "price" (converge only), "shard" (a slice's per-part files only), "combine" (refuses until
    every part's file is there, then the combined record) or "one" (every part, then the combine: one process)."""
    price = getattr(args, "price", None)
    shard = getattr(args, "shard", None)
    combine = bool(getattr(args, "combine", False))
    if sum((price is not None, shard is not None, combine)) > 1:
        raise SystemExit("--price, --shard and --combine are separate steps")
    if price is not None:
        if not price_ok:
            raise SystemExit("--price is converge's")
        return "price"
    return "shard" if shard is not None else "combine" if combine else "one"


def build_part_record(which, file_sha256, audio_sha256, values, pass_used, end, reached, identical_to_x,
                      identical_to_now=None):
    """(Pure.) One part's entry in build-<which>.json (BUILD_PART_FIELDS)."""
    rec = {"file_sha256": file_sha256, "audio_sha256": audio_sha256, "values": values, "pass_used": pass_used,
           "end": end, "reached": bool(reached)}
    if which == "bench":
        rec["identical_to_now"] = bool(identical_to_now)
    elif which != "real":
        raise ValueError(which)
    rec["identical_to_x"] = bool(identical_to_x)
    return rec


def build_record(which, rule, stop, bench_sha, per):
    """(Pure.) build-<which>.json (BUILD_FIELDS) from the per-part files ({pkey: {"record", "rule_off_is_x"?}}), in
    key order; the hits are the parts whose fit reached the stop."""
    keys = sorted(per)
    parts = {k: per[k]["record"] for k in keys}
    hits = [{"part": k, "candidate": rule, "end": parts[k]["end"], "pass_used": parts[k]["pass_used"]}
            for k in keys if parts[k]["reached"]]
    if which == "bench":
        return {"plan": PLAN, "renders": 0, "row": FIX_ROW, "input": RD.DECIDING_INPUT, "rule": rule, "stop": stop,
                "bench_sha256": bench_sha, "parts_n": len(parts), "hits": hits,
                "identical_to_now": sum(r["identical_to_now"] for r in parts.values()), "parts": parts}
    if which == "real":
        return {"plan": PLAN, "renders": 0, "row": REAL_ROW, "build": RD.REAL_BUILD, "input": "the true DI (measured)",
                "rule": rule, "stop": stop, "bench_sha256": bench_sha, "parts_n": len(parts), "hits": hits,
                "rule_off_is_x": {"held": sum(bool(per[k].get("rule_off_is_x")) for k in keys), "of": len(parts)},
                "identical_to_x": sum(r["identical_to_x"] for r in parts.values()), "parts": parts}
    raise ValueError(which)


def build_part_path(which, pk):
    if which not in BUILDS:
        raise ValueError(which)
    return fit_dir() / f"build-{which}" / f"{SE._f(pk)}.json"


def _missing(paths):
    return [k for k, p in paths.items() if not p.exists()]


# --- converge ------------------------------------------------------------------------------------------------------------------

def _converge_part(p, log=print):
    """Every iterated candidate on one part in in-M, up to MAX_PASSES. -> (record without times, seconds by fit)."""
    fits, secs = {}, {}
    for cid in ITERATED:
        t0 = time.time()
        f = fit(p, p.u, cid, MAX_PASSES)
        secs[cid] = {"seconds": round(time.time() - t0, 2), "passes": len(f["trace"]) - 1}
        fits[cid] = {"end": f["end"], "trace": f["trace"]}
        log(f"{p.key[-40:]}: {cid} ended {f['end']['kind']} at pass {f['end']['at']} ({secs[cid]['seconds']} s)")
    rec = {"plan": PLAN, "part": p.key, "set": p.set, "n": p.n, "input": RD.DECIDING_INPUT,
           "input_sha256": S.npy_sha(p.u), "max_passes": MAX_PASSES, "fits": fits}
    return rec, secs


def converge_record(recs, trace_shas, priced_parts):
    """(Pure.) converge.json from every part's trace: the stop (the largest pass count among fits that repeated) and
    every fit that reaches it with its pass used; no fit repeated: refused."""
    ends = {(k, c): recs[k]["fits"][c]["end"] for k in sorted(recs) for c in ITERATED}
    stop, hit_fits = safety_stop({f"{k}\t{c}": e for (k, c), e in ends.items()})
    if stop is None:
        raise SystemExit(f"no fit repeated within {MAX_PASSES} passes: no stop; to the user")
    hits = []
    for f in hit_fits:
        k, c = f.split("\t")
        t = recs[k]["fits"][c]
        hits.append({"part": k, "candidate": c, "end": t["end"], "pass_used": pass_used(t["trace"], t["end"], stop)})
    return {"plan": PLAN, "renders": 0, "input": RD.DECIDING_INPUT, "max_passes": MAX_PASSES, "stop": stop,
            "fits": len(ends), "hits": hits, "ends": end_summary(ends),
            "parts": {k: {"trace_sha256": trace_shas[k]} for k in sorted(recs)}, "priced_parts": priced_parts}


def cmd_converge(args):
    """converge (zero renders).
    `--price N` (2 or 3; amendment 2): the first N parts by key, every iterated candidate up to 64 passes, one compose
    timed per part; the projected wall of the full run (at the priced fits' mean passes, and at 64) and of the later
    runs (`bench`'s in-U and in-F, `build-bench`, `build-real`) for the costliest candidate; price.json (written once).
    The priced parts' traces are kept for the full run.
    The rest is refused until price.json exists. No flag: every iterated candidate on the 47 in in-M up to 64 passes
    (a part already traced is kept), then the combine. `--shard k/n`: that slice's traces only. `--combine`: refused
    until every part is traced; the stop and every fit that reaches it, converge.json (written once)."""
    m = require_fit()
    mode = run_mode(args, price_ok=True)
    keys = _main_parts(m)
    if mode == "price":
        n_price = args.price
        if n_price not in PRICE_PARTS:
            raise SystemExit(f"--price takes {PRICE_PARTS} parts")
        NT.never_overwrite(price_path())
        keys = keys[:n_price]
        if any(trace_path(k).exists() for k in keys):
            raise SystemExit("a priced part is traced already: no timing to price from")
        timing, compose, lengths = {}, {}, {}
        for p in bench_parts(m, set(keys)):
            rec, timing[p.key] = _converge_part(p)
            t0 = time.time()
            guitar(p, rec["fits"][ITERATED[0]]["trace"][0]["values"])
            compose[p.key] = round(time.time() - t0, 3)
            lengths[p.key] = p.n
            _save_once(trace_path(p.key), rec)
        out = price_body(timing, lengths, _part_lengths(m), NR.SR, compose)
        out.update(time=time.strftime("%Y-%m-%d %H:%M:%S"))
        sha = _save_once(price_path(), out)
        lat = out["later"]
        print(f"RF PRICE: {out['priced_fits']} fits on {len(keys)} parts, {out['seconds_per_pass_per_audio_s']:.4f} s "
              f"per pass per second of audio; projected wall of converge on one process "
              f"{out['projected_hours_mean']:.2f} h at the priced mean of {out['passes_mean']:.1f} passes, "
              f"{out['projected_hours_worst']:.2f} h at {MAX_PASSES}; price.json sha256 {sha}")
        for c, r in out["by_candidate"].items():
            print(f"  {c}: {r['seconds_per_pass_per_audio_s']:.4f} s per pass per second of audio, mean "
                  f"{r['passes_mean']:.1f} passes")
        print(f"  the later runs for the costliest ({lat['candidate']}): {lat['fits_per_part']} fits a part "
              f"{lat['hours_mean']:.2f} h at its mean passes, {lat['hours_worst']:.2f} h at {MAX_PASSES}, plus "
              f"{lat['compose_hours']:.2f} h of composes; by step at its mean passes {lat['by_step_hours_mean']}")
        return
    price = _load_checked(price_path(), None, "converge --price 2")      # a gate only: its times are not in the chain
    if mode != "shard":
        NT.never_overwrite(converge_path())
    want = ladder_inputs(m)
    if mode in ("one", "shard"):
        mine = shard_keys(keys, getattr(args, "shard", None))
        need = _missing({k: trace_path(k) for k in mine})
        why = trace_refusal({k: json.loads(trace_path(k).read_text()) for k in mine if k not in need}, want)
        if why:                                                          # a trace kept from before: of this input
            raise SystemExit(why)
        t0 = time.time()
        if need:
            for p in bench_parts(m, set(need)):
                rec, _ = _converge_part(p)
                _save_once(trace_path(p.key), rec)
                print(f"{p.key[-40:]}: traced ({time.time() - t0:.0f} s in all)", flush=True)
        if mode == "shard":
            print(f"RF CONVERGE SHARD {args.shard[0]}/{args.shard[1]}: {len(mine)} parts traced ({len(need)} new, "
                  f"{time.time() - t0:.0f} s); `converge --combine` once every shard is done")
            return
    missing = _missing({k: trace_path(k) for k in keys})
    if missing:
        raise SystemExit(f"{len(missing)} of {len(keys)} parts are not traced yet: run every shard first")
    recs = {k: json.loads(trace_path(k).read_text()) for k in keys}
    if any(sorted(r["fits"]) != sorted(ITERATED) or r["input"] != RD.DECIDING_INPUT for r in recs.values()):
        raise SystemExit("a trace is not of every iterated candidate in in-M")
    why = trace_refusal(recs, want)
    if why:
        raise SystemExit(why)
    out = converge_record(recs, {k: S.file_sha(trace_path(k)) for k in keys}, price["priced_parts"])
    sha = _save_once(converge_path(), out)
    print(f"RF CONVERGE: {out['fits']} fits; the stop {out['stop']} passes; {len(out['hits'])} fits reach it; "
          f"converge.json sha256 {sha}")
    for h in out["hits"]:
        print(f"  reaches the stop: {h['part'][-40:]} {h['candidate']} ({h['end']['kind']} at {h['end']['at']}), "
              f"pass used {h['pass_used']}")


def ladder_inputs(m):
    """Each part's in-M input sha256 as main's ladder records it (`inputs["in-M"]["input_sha256"]`, each part record
    checked against ladder.json's, itself main's `phase_scratch_rederive_ladder`). -> {pkey: sha256}."""
    lad = NT.require_file_hash(m, RD.PHASE_LADDER, RD.ladder_path())
    return {k: _load_checked(RD.part_path(k), lad["parts"][k]["record_sha256"], "scratch_rederive ladder")
            ["inputs"][RD.DECIDING_INPUT]["input_sha256"] for k in sorted(lad["parts"])}


def trace_refusal(recs, want):
    """(Pure.) Why traces may not be used, or None: each trace's `input_sha256` must be the ladder's in-M input for its
    part (a trace kept from an earlier run, a shard's or the price's, is never of another input). recs: {pkey: trace};
    want: {pkey: sha256} (`ladder_inputs`)."""
    bad = sorted(k for k, r in recs.items() if k not in want or r.get("input_sha256") != want[k]
                 or r.get("part") != k)
    if bad:
        return (f"{len(bad)} trace(s) are not of the ladder's in-M input ({', '.join(part_tag(k) for k in bad)}): "
                "never used; to the user")
    return None


def _part_lengths(m):
    lad = NT.require_file_hash(m, RD.PHASE_LADDER, RD.ladder_path())
    return {k: json.loads(RD.part_path(k).read_text())["n"] for k in lad["parts"]}


def price_body(timing, priced_n, all_n, rate, compose_s=None):
    """(Pure.) The projected walls from the priced fits, on one process. Converge: seconds per pass per second of audio
    over the priced fits, times the 47 parts' audio, the iterated candidates and the passes (the priced fits' mean,
    and MAX_PASSES). The later runs: for the costliest candidate (the most seconds per fit per second of audio), its
    LATER_FITS fits a part at its own rate (its mean passes, and MAX_PASSES), and LATER_COMPOSES composes a part at
    the priced compose rate (compose_s: {pkey: seconds of one compose})."""
    secs = sum(f["seconds"] for t in timing.values() for f in t.values())
    work = sum(f["passes"] * priced_n[k] / rate for k, t in timing.items() for f in t.values())
    passes = [f["passes"] for t in timing.values() for f in t.values()]
    rate_s = secs / work if work > 0 else math.nan
    audio = sum(all_n.values()) / rate
    mean_p = statistics.mean(passes) if passes else math.nan
    by_c = {}
    for c in ITERATED:
        rows = [(k, t[c]) for k, t in timing.items() if c in t]
        if not rows:
            continue
        w = sum(f["passes"] * priced_n[k] / rate for k, f in rows)
        by_c[c] = {"seconds_per_pass_per_audio_s": sum(f["seconds"] for _, f in rows) / w if w > 0 else math.nan,
                   "passes_mean": statistics.mean(f["passes"] for _, f in rows),
                   "seconds_per_fit_per_audio_s": (sum(f["seconds"] for _, f in rows)
                                                   / sum(priced_n[k] / rate for k, _ in rows))}
    later = None
    if by_c:
        c = max(by_c, key=lambda x: (by_c[x]["seconds_per_fit_per_audio_s"], x))
        r, pm = by_c[c]["seconds_per_pass_per_audio_s"], by_c[c]["passes_mean"]
        comp = (sum(compose_s.values()) / sum(priced_n[k] / rate for k in compose_s)) if compose_s else math.nan
        nfit = sum(LATER_FITS.values())
        later = {"candidate": c, "fits_per_part": nfit, "composes_per_part": LATER_COMPOSES,
                 "seconds_per_compose_per_audio_s": comp,
                 "hours_mean": r * audio * nfit * pm / 3600, "hours_worst": r * audio * nfit * MAX_PASSES / 3600,
                 "compose_hours": comp * audio * LATER_COMPOSES / 3600,
                 "by_step_hours_mean": {s: round(r * audio * k * pm / 3600, 2) for s, k in LATER_FITS.items()}}
    return {"plan": PLAN, "renders": 0, "priced_parts": len(timing), "priced_fits": len(passes),
            "seconds": round(secs, 1), "seconds_per_pass_per_audio_s": rate_s, "passes_mean": mean_p,
            "passes_max": max(passes) if passes else None, "parts_all": len(all_n), "audio_s_all": audio,
            "projected_hours_mean": rate_s * audio * len(ITERATED) * mean_p / 3600,
            "projected_hours_worst": rate_s * audio * len(ITERATED) * MAX_PASSES / 3600,
            "by_candidate": by_c, "later": later, "compose_s": dict(sorted((compose_s or {}).items())),
            "by_part": {k: {c: dict(f) for c, f in t.items()} for k, t in sorted(timing.items())}}


def end_summary(ends):
    """(Pure.) Per iterated candidate: the fits that repeated, cycled and reached the limit, and the repeat passes'
    median and largest. ends: {(part, cid): end}."""
    out = {}
    for c in ITERATED:
        es = [e for (k, cc), e in ends.items() if cc == c]
        rep = [e["at"] for e in es if e["kind"] == "repeat"]
        out[c] = {"fits": len(es), "repeat": len(rep), "cycle": sum(e["kind"] == "cycle" for e in es),
                  "limit": sum(e["kind"] == "limit" for e in es),
                  "repeat_at_median": statistics.median(rep) if rep else None, "repeat_at_max": max(rep) if rep else None}
    return out


# --- bench ---------------------------------------------------------------------------------------------------------------------

def _interval_40():
    """set_rows' BKS+GOAT pool on the 40 ({pkey: value} -> {mean, lo90, hi90})."""
    from learn import scratch_notes as SN

    draw, sd = SE.context()

    def iv(vals):
        r = SN.set_rows(sd, draw, {k: v for k, v in vals.items() if v is not None and math.isfinite(v)})
        return ((r or {}).get("bks_goat") or {}).get("all")
    return iv


def _bench_part(p, traces, stop):
    """Stage A on one part: every rule's values (from converge's traces), its finished guitar and figures."""
    import numpy as np

    made, out = {}, {}
    for cid in ORDER:
        v, k, hit = values_for(traces, cid, stop)
        key = RD.values_key(v)
        if key not in made:
            made[key] = guitar(p, v)
        y32 = made[key]
        sha = S.npy_sha(y32)
        out[cid] = {"values": v, "pass_used": k, "reached": hit, "sha256": sha, "identical_to_x": sha == p.x_sha,
                    "identical_to_now": sha == p.now_sha,
                    "values_identical_to_t": RD.values_key(v) == RD.values_key(p.T),
                    "logmel_to_x": _finite(NR.logmel_distance(p.X, np.asarray(y32, np.float64))),
                    "errors": RD.value_errors(RD.values_json(p.T), v)}
    if out[TODAY]["sha256"] != p.now_sha:
        raise SystemExit(f"{p.key}: today's rule is not the ladder's xf-now")
    return {"plan": PLAN, "part": p.key, "set": p.set, "stop": stop, "rules": out, "distinct_guitars": len(made)}


def _beside_forms(p, rule, stop):
    """Stage B on one part, beside: the picked rule and today's rule handed in-U and in-F, distance to X."""
    import numpy as np

    out = {}
    for kind in ("in-U", "in-F"):
        u = p.form(kind)
        for cid in dict.fromkeys((TODAY, rule)):
            f = fit(p, u, cid, stop)
            y32 = guitar(p, f["values"])
            out.setdefault(kind, {})[cid] = {"logmel_to_x": _finite(NR.logmel_distance(p.X, np.asarray(y32, np.float64))),
                                             "pass_used": f["pass_used"], "end": f["end"], "reached": f["reached"],
                                             "identical_to_x": S.npy_sha(y32) == p.x_sha}
    return out


def _bench_pick(conv, keys):
    """The pick from every part's stage-A record, or None while any is missing. -> (pick, records) or None."""
    if _missing({k: bench_part_path(k) for k in keys}):
        return None
    recs = {k: json.loads(bench_part_path(k).read_text()) for k in keys}
    if any(r["stop"] != conv["stop"] for r in recs.values()):
        raise SystemExit("a bench record has another stop")
    deciding = [k for k in keys if recs[k]["set"] in RD.DECIDING]
    dist = {c: {k: recs[k]["rules"][c]["logmel_to_x"] for k in deciding} for c in ORDER}
    if any(v is None for d in dist.values() for v in d.values()):
        raise SystemExit("a distance on the 40 is not finite: a bug, to the user")
    return pick(dist, _interval_40()), recs


def cmd_bench(args):
    """bench (zero renders). Stage A, per part (all 47): every rule's values from converge's traces under the stop, its
    finished guitar's logmel distance to X, its errors against T and the byte-identical counts. The pick on the 40
    (`pick`) once every part's stage A is there. Stage B, per part, beside: the picked rule and today's rule in in-U
    and in-F. No flag: both stages on every part, then the combine. `--shard k/n`: that slice's stage A, then, when
    every part's stage A is there, its stage B (else rerun the shard once every shard's stage A is done).
    `--combine`: refused until both stages are there for every part; bench.json (written once)."""
    m = require_fit()
    mode = run_mode(args)
    if mode != "shard":
        NT.never_overwrite(bench_path())
    conv = _load_checked(converge_path(), None, "converge")
    stop, keys = conv["stop"], sorted(conv["parts"])
    t0 = time.time()
    if mode in ("one", "shard"):
        shard = getattr(args, "shard", None)
        mine = shard_keys(keys, shard)
        need = _missing({k: bench_part_path(k) for k in mine})
        if need:
            for p in bench_parts(m, set(need)):
                traces = _load_checked(trace_path(p.key), conv["parts"][p.key]["trace_sha256"], "converge")["fits"]
                rec = _bench_part(p, traces, stop)
                _save_once(bench_part_path(p.key), rec)
                print(f"{p.key[-40:]}: stage A, {rec['distinct_guitars']} distinct guitars; today's rule "
                      f"{rec['rules'][TODAY]['logmel_to_x']:.3f} from X ({time.time() - t0:.0f} s in all)", flush=True)
        got = _bench_pick(conv, keys)
        if got is None:
            if mode == "one":
                raise SystemExit("stage A is missing for some parts: a bug, to the user")
            print(f"RF BENCH SHARD {shard[0]}/{shard[1]}: stage A done; the pick waits for every part's stage A: "
                  "rerun this shard once every shard's stage A is done")
            return
        rule = got[0]["candidate"]
        need = _missing({k: beside_part_path(k) for k in mine})
        if need:
            for p in bench_parts(m, set(need)):
                _save_once(beside_part_path(p.key), {"plan": PLAN, "part": p.key, "rule": rule, "stop": stop,
                                                     "forms": _beside_forms(p, rule, stop)})
                print(f"{p.key[-40:]}: stage B ({time.time() - t0:.0f} s in all)", flush=True)
        if mode == "shard":
            print(f"RF BENCH SHARD {shard[0]}/{shard[1]}: stages A and B done on {len(mine)} parts; `bench --combine` "
                  "once every shard is done")
            return
    got = _bench_pick(conv, keys)
    if got is None:
        raise SystemExit("stage A is not there for every part: run every shard first")
    pk, recs = got
    rule = pk["candidate"]
    missing = _missing({k: beside_part_path(k) for k in keys})
    if missing:
        raise SystemExit(f"stage B is not there for {len(missing)} parts: run every shard again")
    beside = {}
    for k in keys:
        b = json.loads(beside_part_path(k).read_text())
        if (b["rule"], b["stop"]) != (rule, stop):
            raise SystemExit(f"{k}: its beside record is of another rule or stop")
        beside[k] = b["forms"]
    deciding = [k for k in keys if recs[k]["set"] in RD.DECIDING]
    out = {"plan": PLAN, "renders": 0, "input": RD.DECIDING_INPUT, "stop": stop,
           "converge_sha256": S.file_sha(converge_path()), "pick": pk, "parts_n": len(recs), "deciding_n": len(deciding),
           "sets": {k: recs[k]["set"] for k in keys},
           "summary": {"the_40": bench_summary(recs, deciding), "all_47": bench_summary(recs, keys)},
           "beside_forms": beside_summary(beside, deciding, rule),
           "beside_sha256": {k: S.file_sha(beside_part_path(k)) for k in keys},
           "parts": {k: {"record_sha256": S.file_sha(bench_part_path(k)),
                         "picked_values": recs[k]["rules"][rule]["values"],
                         "picked_pass_used": recs[k]["rules"][rule]["pass_used"],
                         "picked_sha256": recs[k]["rules"][rule]["sha256"]} for k in keys}}
    sha = _save_once(bench_path(), out)
    print(f"RF BENCH: picked {rule} (lowest {pk['lowest']}, ties {pk['ties']}); bench.json sha256 {sha}")
    for c in ORDER:
        s = out["summary"]["the_40"][c]
        print(f"  {c}: {pk['means'][c]:.4f} on the 40 (pooled), identical to X {s['identical_to_x']} of "
              f"{len(deciding)}; less the lowest {pk['less_lowest'].get(c)}")


def bench_summary(recs, keys):
    """(Pure.) Per rule over `keys`: the mean distance to X, the parts byte-identical to X and to xf-now, the values
    identical to T, the parts whose fit reached the stop, and the value errors (beside)."""
    out = {}
    for c in ORDER:
        rows = [recs[k]["rules"][c] for k in keys]
        err = [r["errors"] for r in rows]
        tilt = [e["tilt_db_s"] for e in err if e["tilt_part"]]
        out[c] = {"logmel_to_x_mean": RD._mean([r["logmel_to_x"] for r in rows]),
                  "identical_to_x": sum(r["identical_to_x"] for r in rows),
                  "identical_to_now": sum(r["identical_to_now"] for r in rows),
                  "values_identical_to_t": sum(r["values_identical_to_t"] for r in rows),
                  "reached_stop": sum(r["reached"] for r in rows),
                  "tuning_error_median_cents": RD._median([e["tuning_cents"] for e in err]),
                  "tilt_error_mean_db_s": RD._mean(tilt), "tilt_parts": len(tilt),
                  "level_error_median_db": RD._median([x for e in err for x in e["levels_db"]]),
                  "mutes_extra": sum(e["mutes"]["extra"] for e in err),
                  "mutes_missed": sum(e["mutes"]["missed"] for e in err)}
    return out


def beside_summary(beside, deciding, rule):
    """(Pure.) The picked rule and today's in in-U and in-F: mean distance to X on the 40 and all 47."""
    out = {}
    for kind in ("in-U", "in-F"):
        for cid in dict.fromkeys((TODAY, rule)):
            vals = {k: beside[k][kind][cid]["logmel_to_x"] for k in beside}
            out.setdefault(kind, {})[cid] = {"the_40": RD._mean([vals[k] for k in deciding]),
                                             "all_47": RD._mean(list(vals.values())),
                                             "identical_to_x": sum(beside[k][kind][cid]["identical_to_x"]
                                                                   for k in beside),
                                             "reached_stop": sum(beside[k][kind][cid]["reached"] for k in beside)}
    return out


# --- the builds ---------------------------------------------------------------------------------------------------------------

def _build_part(which, p, rule, stop, bench, bench_sha):
    """One part's guitar and per-part file. bench: the picked rule handed in-M, equal to the bench's values and
    sha256 (today's rule: xf-now's guitar). real: first the rule off on the true DI must be X; then the picked rule
    handed the true DI."""
    extra = {}
    if which == "bench":
        f = fit(p, p.u, rule, stop)
        if RD.values_key(f["values"]) != RD.values_key(bench["parts"][p.key]["picked_values"]):
            raise SystemExit(f"{p.key}: the fit does not repeat the bench's values: a bug, to the user")
        y32 = guitar(p, f["values"])
        sha = S.npy_sha(y32)
        if sha != bench["parts"][p.key]["picked_sha256"] or (rule == TODAY and sha != p.now_sha):
            raise SystemExit(f"{p.key}: the guitar is not the bench's")
        fs = RD._write_once(guitar_path(FIX_ROW, p.key), y32)
        rec = build_part_record("bench", fs, sha, f["values"], f["pass_used"], f["end"], f["reached"],
                                sha == p.x_sha, sha == p.now_sha)
    else:
        if S.npy_sha(guitar(p, fit(p, p.di, TODAY)["values"])) != p.x_sha:
            raise SystemExit(f"{p.key}: the rule off on the true DI is not X: a bug, to the user")
        extra = {"rule_off_is_x": True}
        f = fit(p, p.di, rule, stop)
        y32 = guitar(p, f["values"])
        sha = S.npy_sha(y32)
        fs = RD._write_once(guitar_path(REAL_ROW, p.key), y32)
        rec = build_part_record("real", fs, sha, f["values"], f["pass_used"], f["end"], f["reached"], sha == p.x_sha)
    _save_once(build_part_path(which, p.key), {"plan": PLAN, "part": p.key, "build": which, "rule": rule,
                                               "stop": stop, "bench_sha256": bench_sha, **extra, "record": rec})


def _cmd_build(which, args):
    m = require_fit()
    mode = run_mode(args)
    rp = build_record_path(which)
    if mode != "shard":
        NT.never_overwrite(rp)
    conv = _load_checked(converge_path(), None, "converge")
    bench = _load_checked(bench_path(), None, "bench")
    if bench["converge_sha256"] != S.file_sha(converge_path()):
        raise SystemExit("bench.json was not made from this converge.json")
    rule, stop, bench_sha = bench["pick"]["candidate"], conv["stop"], S.file_sha(bench_path())
    keys = sorted(bench["parts"])
    row = BUILDS[which]
    t0 = time.time()
    if mode in ("one", "shard"):
        shard = getattr(args, "shard", None)
        mine = shard_keys(keys, shard)
        need = _missing({k: build_part_path(which, k) for k in mine})
        if need:
            for p in bench_parts(m, set(need)):
                _build_part(which, p, rule, stop, bench, bench_sha)
                print(f"{p.key[-40:]}: {row} written ({time.time() - t0:.0f} s in all)", flush=True)
        if mode == "shard":
            print(f"RF BUILD-{which.upper()} SHARD {shard[0]}/{shard[1]}: {len(mine)} parts ({len(need)} new); "
                  f"`build-{which} --combine` once every shard is done")
            return
    missing = _missing({k: build_part_path(which, k) for k in keys})
    if missing:
        raise SystemExit(f"{len(missing)} of {len(keys)} parts have no {row} guitar yet: run every shard first")
    per = {}
    for k in keys:
        r = json.loads(build_part_path(which, k).read_text())
        if (r["build"], r["rule"], r["stop"], r["bench_sha256"]) != (which, rule, stop, bench_sha):
            raise SystemExit(f"{k}: its {row} file was made with another rule, stop or bench")
        if S.file_sha(guitar_path(row, k)) != r["record"]["file_sha256"]:
            raise SystemExit(f"{k}: its {row} guitar changed since its file")
        if which == "real" and not r.get("rule_off_is_x"):
            raise SystemExit(f"{k}: the rule off was not X")
        per[k] = r
    out = build_record(which, rule, stop, bench_sha, per)
    sha = _save_once(rp, out)
    print(f"RF BUILD-{which.upper()}: {out['parts_n']} {row} guitars, {len(out['hits'])} fits reach the stop"
          + (f", the rule off is X on {out['rule_off_is_x']['held']} of {out['parts_n']}" if which == "real" else
             f", {out['identical_to_now']} identical to xf-now") + f"; build-{which}.json sha256 {sha}")


def cmd_build_bench(args):
    """build-bench (zero renders): the xf-fix guitars, the picked rule handed in-M under the stop, on all 47 (each
    equal to the bench's picked values and sha256; today's rule picked: each is xf-now's guitar). Per part a guitar
    under dry/xf-fix/ and a file under fit/build-bench/, each written once. No flag: every part, then the combine;
    `--shard k/n`: that slice; `--combine`: refused until every part is there; build-bench.json (BUILD_FIELDS,
    written once)."""
    _cmd_build("bench", args)


def cmd_build_real(args):
    """build-real (zero renders): the rf2 guitars, build 2's notes, the picked rule handed the true DI (the measured
    form build 2 was rebuilt from) under the bench's stop (amendment 5), on all 47. Per part first the rule off: today's
    rule on the true DI must be X (build 2's tr-di, `rebuild_redo`'s output) byte for byte. The real fits that reach
    the stop are listed. Shards and the combine as `build-bench`'s; build-real.json (BUILD_FIELDS, written once)."""
    _cmd_build("real", args)


def cmd_freeze(_args):
    """freeze (zero renders), once: the rule, the stop, both lists of fits that reach it and both builds' sha256
    (`freeze_body`, FREEZE_FIELDS), frozen.json (written once); prints the ledger body for
    `phase_scratch_rederive_frozen` (with frozen.json's sha256). It does not edit the ledger."""
    require_fit()
    NT.never_overwrite(frozen_path())
    conv = _load_checked(converge_path(), None, "converge")
    bench = _load_checked(bench_path(), None, "bench")
    builds = {w: _load_checked(build_record_path(w), None, f"build-{w}") for w in BUILDS}
    for w, b in builds.items():
        for k, r in b["parts"].items():
            if S.file_sha(guitar_path(BUILDS[w], k)) != r["file_sha256"]:
                raise SystemExit(f"{BUILDS[w]}'s guitar changed since its build")
    shas = {"converge": S.file_sha(converge_path()), "bench": S.file_sha(bench_path()),
            "build_bench": S.file_sha(build_record_path("bench")), "build_real": S.file_sha(build_record_path("real"))}
    body = freeze_body(conv, bench, builds, shas)
    sha = _save_once(frozen_path(), body)
    print(json.dumps({RD.PHASE_FROZEN: {"sha256": sha, **body}}, indent=1))


COMMANDS = {"converge": cmd_converge, "bench": cmd_bench, "build-bench": cmd_build_bench,
            "build-real": cmd_build_real, "freeze": cmd_freeze}
SHARDED = ("converge", "bench", "build-bench", "build-real")


def main(argv=None):
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    for p_ in (str(root), str(root / "research")):
        if p_ not in sys.path:
            sys.path.insert(0, p_)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=sorted(COMMANDS))
    ap.add_argument("--price", type=int, default=None, help="converge only: price on this many parts (2 or 3)")
    ap.add_argument("--shard", type=shard_arg, default=None, help=f"k/n (n <= {SHARD_MAX}): this slice of the parts")
    ap.add_argument("--combine", action="store_true", help="refused until every part is there; the combined record")
    args = ap.parse_args(argv)
    if args.price is not None and args.cmd != "converge":
        ap.error("--price is converge's")
    if (args.shard is not None or args.combine) and args.cmd not in SHARDED:
        ap.error(f"--shard and --combine are {SHARDED}'s")
    COMMANDS[args.cmd](args)


if __name__ == "__main__":
    main()
