"""The K_S ceiling extension (`learn/ks_extend.py`, docs/ks-ceiling-extend-plan.md): the stopping
rule, the continuation and its resume, the replay prior, the curves and the report. Fake
objectives, plus checks on the stored knob-ceiling data where it exists (zero renders)."""

import json
import math
import random
import statistics

import pytest

pytest.importorskip("numpy")
pytest.importorskip("scipy")

from learn import arm_a_levers as L  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn import ks_extend as X  # noqa: E402

AMP = "sw50r"


def preset(seed, mics=("3", "5"), switches="false"):
    rng = random.Random(seed)
    x = {("parameters", "outputGain"): "5.96", ("cabParameters", "leftCabActive"): "true"}
    for d in K.space(AMP):
        if d.kind == "cat":
            x[(d.module, d.key)] = mics[0] if d.key.startswith("left") else mics[1]
        elif d.kind == "switch":
            x[(d.module, d.key)] = switches
        else:
            x[(d.module, d.key)] = K.fmt(d.from_unit(rng.random()))
    return x


S = preset(1)
DIMS = K.space(AMP, S)


def k(d):
    return (d.module, d.key)


def toy(target_seed=9, held_scale=1.1):
    """A smooth toy distance with a known optimum; the held half is a scaled, slightly shifted copy."""
    t = preset(target_seed, mics=("4", "6"), switches="true")

    def dist(x, shift=0.0):
        v = sum((d.to_unit(x[k(d)]) - d.to_unit(t[k(d)]) - shift) ** 2 for d in DIMS if d.kind in ("cont", "log"))
        v += sum(0.05 * (x[k(d)] != t[k(d)]) for d in DIMS if d.kind in ("cat", "switch"))
        return 1.0 + v

    def render(x):
        return {"A": dist(x), "B": held_scale * dist(x, 0.02)}
    return render


class Counted:
    def __init__(self, render):
        self.render, self.keys = render, []

    def __call__(self, x):
        self.keys.append(K.key(x))
        return self.render(x)


def stored_search(render, budget=150, search="A"):
    """A 'stored' K_S search on the toy: (evals [(A, B)], final x)."""
    evals = []

    def f(x):
        d = render(x)
        evals.append((d["A"], d["B"]))
        return d[search]
    x, _, _, _ = K.knob_search(DIMS, S, f, budget, K.SEED)
    return evals, x


def start_of(evals, search="A"):
    held = "B" if search == "A" else "A"
    c = X.incumbent_curve(evals, search, held)[-1]
    return {search: c[0], held: c[1]}


# --- the stopping rule ------------------------------------------------------------------------------

def test_rule_needs_a_full_window_before_flat():
    assert X.stop_reason([1.0, 1.0]) is None                     # 50 renders
    assert X.stop_reason([1.0, 1.0, 1.0]) is None                # 100
    assert X.stop_reason([1.0, 1.0, 1.0, 1.0]) == "flat"         # 150, no gain


def test_rule_reads_the_last_window_only():
    best = [2.0, 1.0, 1.0, 1.0, 0.999]                           # big gain early, little in the last 150
    assert X.stop_reason(best) == "flat"
    best = [1.0, 1.0, 1.0, 1.0, 1.0 * math.exp(-0.006)]          # 0.006 in the last 150
    assert X.stop_reason(best) is None


def test_rule_threshold_is_strict_below_min_gain():
    assert X.stop_reason([1.0, 1.0, 1.0, math.exp(-0.0049)]) == "flat"
    assert X.stop_reason([1.0, 1.0, 1.0, math.exp(-0.0051)]) is None


def test_guard_stops_at_600_and_flat_wins_a_tie():
    improving = [math.exp(-0.01 * i) for i in range(13)]          # 0, 50, ..., 600
    assert X.stop_reason(improving[:12]) is None
    assert X.stop_reason(improving) == "guard"
    assert X.stop_reason([1.0] * 13) == "flat"


def test_would_stop_on_stored_curves():
    assert X.would_stop([1.0] * 200) == 150
    assert X.would_stop([1.0 - 0.001 * i for i in range(200)]) is None
    assert X.would_stop([1.0] * 149) is None                      # shorter than one window


# --- the continuation ----------------------------------------------------------------------------------

def test_first_render_repeats_the_stored_final_and_a_moved_repeat_stops():
    render = toy()
    evals, x0 = stored_search(render)
    rec = Counted(render)
    res = X.extend(DIMS, x0, rec, "A", "B", start_of(evals))
    assert rec.keys[0] == K.key(x0) and res["repeat_dev"] < 1e-12
    with pytest.raises(RuntimeError, match="repeat"):
        X.extend(DIMS, x0, lambda x: {"A": render(x)["A"] * 1.01, "B": render(x)["B"]}, "A", "B", start_of(evals))


def test_continuation_improves_stops_flat_and_reports_its_renders():
    render = toy()
    evals, x0 = stored_search(render, budget=60)          # a short stored search: room to improve
    start = start_of(evals)
    res = X.extend(DIMS, x0, render, "A", "B", start)
    assert res["stop"] in ("flat", "exhausted")
    assert res["final"]["search"] <= start["A"]
    assert res["final"]["search"] < start["A"] * math.exp(-X.MIN_GAIN)
    assert res["renders"] == len(res["log"])
    if res["stop"] == "flat":
        assert res["renders"] % X.CHUNK == 0 and res["renders"] >= X.WINDOW
    assert [c[0] for c in res["chunks"]] == list(range(0, res["chunks"][-1][0] + 1, X.CHUNK))
    best = [c[1] for c in res["chunks"]]
    assert best == sorted(best, reverse=True)                     # the incumbent never gets worse
    assert render(res["x"])["A"] == res["final"]["search"]
    assert K.key(res["x"]) == res["final"]["key"]


def test_guard_stops_a_search_that_keeps_improving():
    n = {"i": 0}

    def render(x):                                                 # every new render beats the last
        n["i"] += 1
        v = math.exp(-0.001 * n["i"])
        return {"A": v, "B": v}
    render_x0 = {"A": math.exp(-0.001), "B": math.exp(-0.001)}
    res = X.extend(DIMS, S, render, "A", "B", render_x0)
    assert res["stop"] == "guard" and res["renders"] == X.GUARD
    assert res["rounds"] >= 4 and res["round_stages"][-1].get("stopped_in_round")


def test_lookups_are_not_rendered_and_use_round_evaluations():
    render = toy()
    evals, x0 = stored_search(render)
    lookup, xr, gains = X.replay(AMP, S, evals, "A")
    assert xr == x0
    rec = Counted(render)
    res = X.extend(DIMS, x0, rec, "A", "B", start_of(evals), lookup=lookup, gains=gains)
    assert set(rec.keys[1:]).isdisjoint(lookup)                   # only the repeat is re-rendered
    assert len(rec.keys) == len(set(rec.keys)) == res["renders"]


def test_the_held_half_never_steers_the_search():
    evals, x0 = stored_search(toy())
    a = X.extend(DIMS, x0, toy(held_scale=1.1), "A", "B", start_of(evals))
    b_render = toy(held_scale=3.0)
    start_b = {"A": start_of(evals)["A"], "B": start_of(evals)["B"] / 1.1 * 3.0}
    b = X.extend(DIMS, x0, b_render, "A", "B", start_b)
    assert [e[0] for e in a["log"]] == [e[0] for e in b["log"]]
    assert a["stop"] == b["stop"] and a["final"]["key"] == b["final"]["key"]


def test_the_other_direction_searches_half_b():
    render = toy()
    evals, x0 = stored_search(render, search="B")
    res = X.extend(DIMS, x0, render, "B", "A", start_of(evals, "B"))
    assert res["final"]["search"] <= start_of(evals, "B")["B"]
    assert res["chunks"][0][1] == start_of(evals, "B")["B"]


def test_a_crashed_direction_resumes_with_zero_repeat_renders():
    render = toy()
    evals, x0 = stored_search(render, budget=60)
    start = start_of(evals)
    full = X.extend(DIMS, x0, render, "A", "B", start)
    assert full["renders"] >= 2 * X.CHUNK
    saved = {}

    def crash(snap):
        saved["log"] = [list(e) for e in snap["log"]]
        if snap["renders"] == 2 * X.CHUNK:
            raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        X.extend(DIMS, x0, render, "A", "B", start, on_chunk=crash)
    rec = Counted(render)
    res_render = X.Resume(rec, saved["log"])
    again = X.extend(DIMS, x0, res_render, "A", "B", start)
    assert again["log"] == full["log"] and again["final"] == full["final"] and again["stop"] == full["stop"]
    assert res_render.live == len(rec.keys) == full["renders"] - 2 * X.CHUNK


def test_resume_refuses_a_diverged_log():
    r = X.Resume(lambda x: {"A": 1.0, "B": 1.0}, [["not-this-key", 1.0, 1.0]])
    with pytest.raises(RuntimeError, match="diverged"):
        r(S)


# --- the replay prior and knob_search's gains ------------------------------------------------------

def test_replay_matches_arm_a_levers_and_returns_main_stage_gains():
    render = toy(13)
    evals, x0 = stored_search(render)
    lookup, x, gains = X.replay(AMP, S, evals, "A")
    traj, xr = L.replay_ks(AMP, S, evals, "A")
    assert x == xr == x0
    assert set(lookup) == {K.key(s) for s, _ in traj}
    assert gains and all(v > 0 for v in gains.values())


def test_knob_search_gains_none_is_unchanged_and_a_prior_steers_the_alts():
    render = toy(14)
    f = lambda x: render(x)["A"]  # noqa: E731
    a = K.knob_search(DIMS, S, f, 150, 0)
    g = {}
    b = K.knob_search(DIMS, S, f, 150, 0, gains=g)
    assert a[0] == b[0] and a[1] == b[1] and a[3] == b[3] and g
    prior = {"cabParameters/rightCabMicLevel": 1e9, "sw50rAmp/sw50rLevel": 1e8, "cabParameters/leftCabDistance": 1e7}
    seen = []

    def rec(x):
        seen.append(dict(x))
        return f(x)
    _, _, _, stages = K.knob_search(DIMS, S, rec, 150, 0, gains=dict(prior))
    m = stages["main"]["renders"]
    x_main = min(seen[:m], key=f)
    alts = seen[m:m + stages["alts"]["renders"]]
    moved = {d.name for x in alts for d in DIMS if d.kind == "cont" and x[k(d)] != x_main[k(d)]}
    assert moved and moved <= set(prior)                           # the alts re-tune the prior's key dims


# --- curves and the report -------------------------------------------------------------------------

def test_incumbent_curve_matches_knob_ceiling_summary():
    render = toy()
    evals, x0 = stored_search(render)
    ev = [{"A": a, "B": b} for a, b in evals]
    s = K.summary(ev, "A", "B", DIMS, x0, S)
    assert [(c[1], c[2]) for c in s["curve"]] == X.incumbent_curve(evals, "A", "B")


def test_tail_is_a_log_ratio_over_the_window():
    curve = [(2.0, 4.0)] * 100 + [(1.0, 2.0)] * 50
    assert X.tail(curve, 50) == pytest.approx((math.log(0.5), math.log(0.5)))
    assert X.tail(curve, 49) == (0.0, 0.0)
    assert X.tail([(1.0, math.inf), (0.5, 1.0)], 5)[1] is None


def fake_result(slug, amp, search, chunks, stop, status="done"):
    """A finished direction: chunks [(extra renders, search, held)], the first the stored final."""
    n = chunks[-1][0]
    return {"slug": slug, "amp": amp, "search_half": search, "held_half": "B" if search == "A" else "A",
            "chunks": [[c[0], c[1], c[2], "k"] for c in chunks], "renders": n, "stop": stop,
            "final": {"renders": n, "search": chunks[-1][1], "held": chunks[-1][2], "key": "k"},
            "repeat_dev": 1e-5, "status": status, "rule": {}, "seed": X.SEED}


def flat_at(n, search, held, s0=1.0, h0=1.0):
    """Chunks for a direction that moves from (s0, h0) to (search, held) at 50 and stays to n."""
    return [(0, s0, h0)] + [(m, search, held) for m in range(50, n + 1, 50)]


def base_of(rows):
    """rows: (slug, band, cls, amp, search, S_held, ks_held) -> base figures."""
    return {(s, a, se): {"slug": s, "band": b, "cls": c, "S_held": sh, "ks_held": kh}
            for s, b, c, a, se, sh, kh in rows}


def test_estimate_adds_the_run_gain_to_every_directions_stored_ceiling():
    base = base_of([("p1", "b1", "clean", "pr12", "A", 2.0, 1.0), ("p1", "b1", "clean", "ac20", "B", 2.0, 0.5),
                    ("p2", "b2", "crunch", "pr12", "A", 2.0, 1.0), ("p3", "b3", "clean", "pr12", "A", 2.0, 1.0)])
    results = {("p1", "pr12", "A"): fake_result("p1", "pr12", "A", flat_at(150, 0.9, 0.9), "flat"),
               ("p2", "pr12", "A"): fake_result("p2", "pr12", "A", flat_at(600, 0.8, 0.8), "guard")}
    rows, left = X.estimate_rows(base, results)
    assert left == ["p3"]
    assert rows[0][2] == pytest.approx(statistics.fmean([math.log(0.5), math.log(0.25)]) + math.log(0.9))
    assert rows[1][2] == pytest.approx(math.log(0.5) + math.log(0.8))
    rows0, _ = X.estimate_rows(base, results, 0)
    assert rows0[1][2] == pytest.approx(math.log(0.5))                  # at 150: the stored ceiling


def test_summarise_by_stop_reason_and_a_fixed_direction_set():
    base = base_of([("p1", "b1", "clean", "pr12", "A", 2.0, 1.0), ("p2", "b2", "clean", "pr12", "A", 2.0, 1.0),
                    ("p3", "b3", "crunch", "pr12", "A", 2.0, 1.0), ("p4", "b4", "clean", "pr12", "A", 2.0, 1.0)])
    refusing = flat_at(300, 0.9, 0.9)
    refusing[2] = (100, 0.95, math.inf)                                  # held refused at one point only
    results = {("p1", "pr12", "A"): fake_result("p1", "pr12", "A", flat_at(150, 0.9, 0.95), "flat"),
               ("p2", "pr12", "A"): fake_result("p2", "pr12", "A", flat_at(600, 0.8, 0.85), "guard"),
               ("p3", "pr12", "A"): fake_result("p3", "pr12", "A", refusing, "flat"),
               ("p4", "pr12", "A"): {"slug": "p4", "amp": "pr12", "search_half": "A", "status": "repeat_failed",
                                     "repeat_dev": 0.02}}
    out = X.summarise(base, results)
    assert out["dropped_refused_held"] == [("p3", "pr12", "A")]
    assert out["repeat_failed"] == [("p4", "pr12", "A")]
    for n, g in out["estimate"].items():                               # the same parts at every point
        assert g["all"]["bands"] == 2 and g["parts_left_out"] == ["p4"]          # p3 dropped, p4 has no run
    assert out["estimate"]["300"]["still_running"] == 1
    assert out["headline"] == {"directions_finished": 3, "converged_by_the_declared_rule": 2, "hit_guard": 1,
                               "guard_share": pytest.approx(1 / 3)}
    eg = out["extension_gain_held"]
    assert eg["flat"]["directions"] == 1 and eg["guard"]["directions"] == 1 and eg["all"]["directions"] == 2
    assert eg["flat"]["band_weighted_mean"] == pytest.approx(math.log(0.95))
    assert out["extension_gain_search"]["guard"]["band_weighted_mean"] == pytest.approx(math.log(0.8))
    assert out["renders"]["stops"] == {"flat": 2, "guard": 1}


def test_summarise_step3_view_leaves_out_the_two_dropped_directions():
    base = base_of([("p1", "b1", "clean", "pr12", "A", 2.0, 1.0),
                    ("telefunken-Gym_Hours-GTR_1", "b2", "clean", "pr12", "A", 2.0, 0.5),
                    ("telefunken-Gym_Hours-GTR_1", "b2", "clean", "ac20", "A", 2.0, 0.5)])
    results = {("p1", "pr12", "A"): fake_result("p1", "pr12", "A", flat_at(150, 1.0, 1.0), "flat"),
               ("telefunken-Gym_Hours-GTR_1", "pr12", "A"):
                   fake_result("telefunken-Gym_Hours-GTR_1", "pr12", "A", flat_at(150, 1.0, 1.0), "flat")}
    out = X.summarise(base, results)
    assert out["estimate"]["150"]["all"]["bands"] == 2
    assert out["estimate_step3_142"]["150"]["bands"] == 1


# --- amendment 1: the batch design and the precision rule ----------------------------------------

PARTS = {**{f"c{i:02d}": "clean" for i in range(19)}, **{f"x{i}": "crunch" for i in range(5)}}
BANDS = {s: f"band{i % 14}" for i, s in enumerate(sorted(PARTS))}


def test_design_covers_every_direction_once_balanced_and_seeded():
    b = X.design(PARTS)
    assert len(b) == 6 and all(len(batch) == 24 for batch in b)
    flat = [d for batch in b for d in batch]
    assert len(set(flat)) == 144
    assert set(flat) == {(s, a, h, "B" if h == "A" else "A") for s in PARTS for a in K.AMPS for h in "AB"}
    for batch in b:
        assert sorted(d[0] for d in batch) == sorted(PARTS)                  # one direction per part
        amps = [sum(d[1] == a for d in batch) for a in K.AMPS]
        halves = sum(d[2] == "A" for d in batch)
        assert max(amps) - min(amps) <= 2 and 11 <= halves <= 13
    for s in PARTS:
        seq = [next(d for d in batch if d[0] == s) for batch in b]
        assert all(x[1] != y[1] and x[2] != y[2] for x, y in zip(seq, seq[1:]))
    assert X.design(PARTS) == b and X.design(PARTS, seed=1) != b
    assert [d[0] for d in b[0]][:19] == [d[0] for d in b[3]][:19]            # seeded order, clean first
    assert all(d[0].startswith("c") for d in b[0][:19])


def test_precision_h_matches_the_formula():
    g = {"p1": [0.0, 0.1], "p2": [0.2, 0.2], "p3": [0.05]}
    bands = {"p1": "a", "p2": "a", "p3": "b"}
    s2 = (0.05 ** 2 * 2) / 2                                                 # pooled: 2 df (p1 1, p2 1)
    want = 1.645 * math.sqrt(s2 / 2 * (1 - 2 / 6) * (1 / 2 + 1 / 1) / 2 ** 2)
    assert X.precision_h(g, 2, bands) == pytest.approx(want)
    assert X.precision_h(g, 6, bands) == 0.0
    assert X.precision_h({"p1": [0.1], "p2": [0.3]}, 1, bands) is None


def _batch_results(batches, k, gain, held=1.0, status="done"):
    out = {}
    for b in batches[:k]:
        for s, a, se, _ in b:
            g = gain(s, a, se)
            out[(s, a, se)] = fake_result(s, a, se, [(0, 1.0, 1.0), (150, math.exp(g), held)], "flat", status)
    return out


def test_walk_waits_for_a_batch_then_needs_two_and_stops_on_h():
    b = X.design(PARTS)
    res = _batch_results(b, 1, lambda s, a, se: -0.05)
    w = X.walk(b, res, BANDS)
    assert w["next"] == 1 and w["history"][0]["decision"] == "continue" and w["history"][0]["h"] is None
    partial = dict(res)
    partial.update({k: v for k, v in list(_batch_results(b, 2, lambda s, a, se: -0.05).items())[24:30]})
    assert X.walk(b, partial, BANDS)["next"] == 1                           # batch 2 unfinished: wait
    same = _batch_results(b, 2, lambda s, a, se: -0.05)                     # no within-part spread: h = 0
    w = X.walk(b, same, BANDS)
    assert w["next"] is None and w["stopped_after"] == 2 and w["history"][-1]["h"] == 0.0
    noisy = _batch_results(b, 2, lambda s, a, se: -0.2 if se == "A" else 0.0)
    w = X.walk(b, noisy, BANDS)
    assert w["next"] == 2 and w["history"][-1]["h"] > X.H_MAX
    w6 = X.walk(b, _batch_results(b, 6, lambda s, a, se: -0.2 if se == "A" else 0.0), BANDS)
    assert w6["stopped_after"] <= 6 and w6["history"][-1]["decision"] == "stop"


def test_walk_never_reads_the_held_half_and_treats_repeat_failures_as_finished():
    b = X.design(PARTS)
    gain = lambda s, a, se: -0.1 if a == "pr12" else -0.02  # noqa: E731
    a = X.walk(b, _batch_results(b, 3, gain, held=1.0), BANDS)
    c = X.walk(b, _batch_results(b, 3, gain, held=math.inf), BANDS)
    assert a == c
    res = _batch_results(b, 2, gain)
    key = b[1][0][:3]
    res[key] = {"slug": key[0], "amp": key[1], "search_half": key[2], "status": "repeat_failed", "repeat_dev": 0.1}
    assert X.walk(b, res, BANDS)["history"][-1]["batches"] == 2


# --- amendment 1: processes, resume and the queue ------------------------------------------------

def test_render_processes_are_python_commands_not_their_wrappers():
    ps = [(10, ".venv/bin/python -m learn.ks_extend run --shard 0/3 --after 1"),
          (11, "zsh -c .venv/bin/python -m learn.ks_extend run --shard 1/3"),
          (12, "/usr/bin/python3 -m learn.song_relabel probe --shard 2/3"),
          (13, ".venv/bin/python -m learn.song_relabel sets"),
          (14, ".venv/bin/python -m learn.ks_extend report"),
          (15, "/opt/x/Python -m learn.song_relabel render-new --shard 0/3")]
    assert X.others_rendering(ps) == [10, 12, 15]
    assert X.others_rendering(ps, own={10}) == [12, 15]
    assert X.queue_pids([12, 13, 11, 99], ps) == [12, 13]                    # 99 gone; 11 a wrapper


def test_a_reused_pid_is_not_waited_for():
    assert X.queue_pids([12], [(12, "/usr/bin/vim notes.txt")]) == []


def test_run_refuses_an_empty_after_without_no_wait():
    with pytest.raises(SystemExit, match="--after is empty"):
        X.cmd_run((0, 3), [], False)


def test_resume_needs_the_same_rule_seed_and_round():
    meta = {"seed": X.SEED, "rule": {"chunk": 50, "window": 150, "min_gain": 0.005, "guard": 600, "round": 150}}
    X.check_saved({**meta}, meta)
    with pytest.raises(SystemExit, match="rule"):
        X.check_saved({**meta, "rule": {**meta["rule"], "round": 100}}, meta)
    with pytest.raises(SystemExit, match="seed"):
        X.check_saved({**meta, "seed": X.SEED + 1}, meta)


def test_a_failed_repeat_carries_its_deviation():
    render = toy()
    evals, x0 = stored_search(render)
    with pytest.raises(X.RepeatFailed) as e:
        X.extend(DIMS, x0, lambda x: {"A": render(x)["A"] * 1.02, "B": render(x)["B"]}, "A", "B", start_of(evals))
    assert e.value.dev == pytest.approx(math.log(1.02))


def stage2_result(per_effect, dry=(1.0, 1.0), wet=False, on=()):
    return {"slug": "p", "band": "b", "gain_class": "clean", "amp": "pr12", "search_half": "A", "held_half": "B",
            "start_search": dry[0], "start_held": dry[1], "per_effect": per_effect, "wet": wet,
            "effects_on": list(on), "held": None}


def test_stage2_choice_follows_the_wet_margin_and_the_budget():
    late = [(1.0, 1.0)] * 13 + [(0.9, 0.8)] * 11                    # the effect's gain comes after 12 renders
    r = stage2_result({"reverb": {"evals": late}, "delay": {"evals": [(0.999, 1.0)] * 24}})
    assert X.stage2_choice(r)[0] == "reverb"
    assert X.stage2_choice(r, 12)[0] == "dry"                       # delay's 0.001 is inside the margin
    r["wet"], r["effects_on"], r["held"] = True, ["reverb"], 0.8
    eff, cells = X.kc2_stage2_rows([r])
    assert cells[0]["matches_stored"] and cells[0]["choice_half"] == "dry"
    assert cells[0]["d_held"] == pytest.approx(math.log(0.8))
    assert {e["effect"] for e in eff} == {"reverb", "delay"}


def test_tail_summary_on_stage1_rows():
    evals = [(1.0 - 0.001 * i, 1.0 - 0.001 * i) for i in range(200)]
    rows = X.kc2_stage1_rows([{"slug": f"p{i}", "band": f"b{i}", "gain_class": "clean", "amp": "pr12",
                               "search_half": "A", "held_half": "B", "evals": evals} for i in range(3)])
    s = X.tail_summary(rows)
    assert s["search"]["median"] == pytest.approx(math.log(0.801 / 0.851))
    assert s["rule_flat_by_budget"] == 0 and s["held"]["bw"]["bands"] == 3


# --- the stored data (zero renders; skipped without it) -----------------------------------------

def _have_kc():
    return (K.OUT / "cells").exists() and (L.SS_OUT / "armB" / "menu-S.json").exists()


@pytest.mark.skipif(not _have_kc(), reason="no stored knob-ceiling data")
def test_stored_ks_directions_replay_with_their_prior():
    ms, ps = L.menu_S(), K.parts()
    dirs = X.directions()
    assert len(dirs) == 144 and not any("Honey" in d[0] for d in dirs)
    for slug, amp, search, _ in dirs[::12]:                           # a sample; the full set runs in `check`
        c = json.loads((K.OUT / "cells" / slug / amp / "result.json").read_text())
        lookup, x, gains = X.replay(amp, ms[amp][ps[slug]["gain_class"]][1], c["runs"][search]["K_S"]["evals"], search)
        assert x == L._settings(K.OUT / "cells" / slug / amp / f"K_S-{search}.json"), (slug, amp, search)
        assert K.key(x) in lookup and gains


@pytest.mark.skipif(not _have_kc(), reason="no stored knob-ceiling data")
def test_stored_ks_tails_reproduce_the_known_figures():
    ps = K.parts()
    rows = X.ks_tail_rows([c for c in X._kc_cells() if c["slug"] in ps])
    assert len(rows) == 144
    held = [r["d_held"] for r in rows]
    assert statistics.median(held) == pytest.approx(-0.0127, abs=5e-4)    # the "+0.013 median" of the brief
    assert statistics.fmean(held) == pytest.approx(-0.0267, abs=5e-4)


@pytest.mark.skipif(not (X.KC2 / "stage2").exists(), reason="no stored knob-ceiling-2 data")
def test_stored_stage2_choices_are_reproduced():
    s2 = [json.loads(p.read_text()) for p in sorted((X.KC2 / "stage2").glob("*/[AB].json"))]
    _, cells = X.kc2_stage2_rows(s2)
    assert len(cells) == 48 and all(c["matches_stored"] for c in cells)


@pytest.mark.skipif(not _have_kc(), reason="no stored knob-ceiling data")
def test_the_report_at_150_reproduces_step_3s_ceiling():
    """Every stored K_S as a direction with no extra renders: the estimate at 150 is step 3's −0.269."""
    base = X.base_figures()
    results = {k: fake_result(k[0], k[1], k[2], [(0, 1.0, b["ks_held"])], "flat") for k, b in base.items()}
    out = X.summarise(base, results)
    assert out["estimate_step3_142"]["150"]["band_weighted_mean"] == pytest.approx(-0.26893, abs=1e-5)
    assert len(base) == 144 and out["estimate"]["150"]["all"]["bands"] == 14


@pytest.mark.skipif(not _have_kc(), reason="no stored knob-ceiling data")
def test_the_real_design_covers_the_144_directions():
    b = X.the_design()
    assert sum(len(x) for x in b) == 144 and all(len(x) == 24 for x in b)
