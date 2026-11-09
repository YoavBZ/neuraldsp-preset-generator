"""C1a (docs/full-controls-plan.md): the pure parts of learn/full_controls.py."""
import json
import math
import re

import pytest

pytest.importorskip("numpy")

from learn import every_control as E  # noqa: E402
from learn import full_controls as F  # noqa: E402
from learn import knob_ceiling as K  # noqa: E402
from learn import knob_ceiling2 as K2  # noqa: E402
from learn import local_objective as LO  # noqa: E402
from learn import pipeline_fix as P  # noqa: E402


def rec(v, search="A", label=True):
    return {"search": search, "best": {"judge": {"A": v, "B": v + 1}}, "label": {} if label else None}


def test_bks_amp_choice_takes_the_lowest_search_half_and_skips_fallbacks():
    assert F.bks_amp_choice({"pr12": rec(3.0), "sw50r": rec(2.5), "ac20": rec(2.9)}) == "sw50r"
    assert F.bks_amp_choice({"pr12": rec(3.0), "sw50r": rec(2.5, label=False), "ac20": rec(2.9)}) == "ac20"
    assert F.bks_amp_choice({"pr12": rec(3.0), "sw50r": rec(float("inf"))}) == "pr12"
    assert F.bks_amp_choice({"pr12": rec(3.0, search="B"), "ac20": rec(2.6, search="B")}) == "ac20"   # B: 4.0 against 3.6
    assert F.bks_amp_choice({}) is None


def test_bks_amp_choice_reads_the_records_own_search_half():
    a = {"search": "B", "best": {"judge": {"A": 1.0, "B": 5.0}}, "label": {}}
    b = {"search": "A", "best": {"judge": {"A": 2.0, "B": 0.5}}, "label": {}}
    assert F.bks_amp_choice({"pr12": a, "ac20": b}) == "ac20"


def records():
    return ([{"set": "n12", "key": f"n{i}"} for i in range(20)] + [{"set": "bks", "key": f"b{i}"} for i in range(30)])


def test_draw_subset_is_seeded_six_a_set():
    s1, s2 = F.draw_subset(records()), F.draw_subset(records())
    assert s1 == s2 and len(s1) == 12
    assert sum(k.startswith("n") for k in s1) == 6 and sum(k.startswith("b") for k in s1) == 6
    assert F.draw_subset(records(), seed=1) != s1
    assert F.draw_subset(list(reversed(records()))) == s1                     # order-free


def test_shard_order_puts_the_subset_first_and_spreads_it():
    rs = [{"key": f"k{i}", "subset": i in (3, 7, 11)} for i in range(12)]
    order = F.shard_order(rs)
    assert [r["subset"] for r in order[:3]] == [True] * 3 and not any(r["subset"] for r in order[3:])
    shards = [[r for j, r in enumerate(order) if j % 3 == k] for k in range(3)]
    assert [sum(r["subset"] for r in s) for s in shards] == [1, 1, 1]


def full_start(amp="pr12"):
    """A whole Morgan setting from the table's neutral values, amp EQ and sections on, pedals off."""
    x = {c.path: c.neutral for c in E.table("morgan") if c.neutral is not None and c.module}
    x.update(K2.HELD_ON)
    x[(f"{amp}EQ", f"{amp}EQActive")] = "true"
    x[("ampParameters", "sectionActive")] = "true"
    x[("cabParameters", "sectionActive")] = "true"
    x[("fxParameters", "sectionActive")] = "true"
    return x


@pytest.mark.parametrize("amp", ["pr12", "sw50r", "ac20"])
def test_c1a_space_has_ft2s_gain_range_the_gate_and_no_mics(amp):
    st = full_start(amp)
    dims = F.c1a_space(amp, st)
    names = [d.name for d in dims]
    g = next(d for d in dims if d.name == "parameters/inputGain")
    assert (g.lo, g.hi) == F.GAIN_DB == (-20.0, 12.0)
    assert names.count("parameters/inputGain") == 1
    assert "parameters/gateActive" in names and "parameters/gateThreshold" in names
    assert not any(d.kind == "cat" for d in dims) and not any("MicType" in n for n in names)
    assert {d.name for d in K.eq_space(amp)} <= set(names)
    assert {d.name for d in K2.pedal_dims()} <= set(names)
    assert len(dims) == len(K2.stage1_space(amp, st)) + 2
    gt = next(d for d in dims if d.name == "parameters/gateThreshold")
    assert (gt.kind, gt.lo, gt.hi) == ("cont", -96.0, 0.0)


def test_make_canon_neutralises_off_pedals_and_an_off_gate_only():
    st = full_start()
    x = dict(st)
    x[("drive1", "drive1Active")] = "false"
    x[("drive1", "drive1Drive")] = "0.9"
    x[("parameters", "gateActive")] = "false"
    x[("parameters", "gateThreshold")] = "-30"
    y = F.make_canon("pr12")(x)
    assert y[("drive1", "drive1Drive")] == K2.PEDALS["drive1"][1]["drive1Drive"]
    assert y[("parameters", "gateThreshold")] == F.GATE_ON_DB == "-80"                  # the factory median
    assert F.make_canon("pr12")(y) == y                                      # idempotent
    x[("drive1", "drive1Active")] = "true"
    x[("parameters", "gateActive")] = "true"
    z = F.make_canon("pr12")(x)
    assert z[("drive1", "drive1Drive")] == "0.9" and z[("parameters", "gateThreshold")] == "-30"


def test_c1a_start_changes_nothing_that_sounds_and_audible_change_catches_what_does():
    lab = full_start()
    lab[("drive2", "drive2Active")] = "false"
    lab[("drive2", "drive2Gain")] = "0.77"                                     # inert: the pedal is off
    lab[("parameters", "gateActive")] = "false"
    lab[("parameters", "gateThreshold")] = "-12"                               # inert: the gate is off
    lab[("pr12EQ", "pr12EQBand3")] = "4.5"                                     # the EQ is on: kept
    label = LO.sdict(lab)
    st = F.c1a_start(label, "pr12")
    assert st[("pr12EQ", "pr12EQBand3")] == "4.5"
    assert st[("drive2", "drive2Gain")] != "0.77"
    assert st[("parameters", "gateActive")] == "true" and st[("parameters", "gateThreshold")] == F.GATE_ON_DB == "-80"
    assert F.audible_change(st, label, "pr12", declared=F.GATE_KEYS) == []      # the gate on: verified by render
    assert F.audible_change(st, label, "pr12") == ["parameters/gateActive", "parameters/gateThreshold"]
    off = dict(lab)
    off[("pr12EQ", "pr12EQActive")] = "false"                                  # an inactive EQ: eq_start flattens it
    st2 = F.c1a_start(LO.sdict(off), "pr12")
    assert "pr12EQ/pr12EQActive" in F.audible_change(st2, LO.sdict(off), "pr12", declared=F.GATE_KEYS)


def test_gate_on_keeps_a_gate_already_on_and_turns_an_off_one_on_at_the_factory_threshold():
    on = {("parameters", "gateActive"): "true", ("parameters", "gateThreshold"): "-42"}
    assert F.gate_on(on) == on
    off = {("parameters", "gateActive"): "false", ("parameters", "gateThreshold"): "-12"}
    assert F.gate_on(off) == {("parameters", "gateActive"): "true", ("parameters", "gateThreshold"): F.GATE_ON_DB}
    lab = full_start()
    lab[("parameters", "gateActive")] = "true"
    lab[("parameters", "gateThreshold")] = "-42"
    st = F.c1a_start(LO.sdict(lab), "pr12")
    assert st[("parameters", "gateThreshold")] == "-42" and F.audible_change(st, LO.sdict(lab), "pr12") == []


def test_ablations_reset_only_their_own_keys_to_the_start():
    st = full_start()
    best = dict(st)
    best[("drive1", "drive1Active")] = "true"
    best[("drive1", "drive1Drive")] = "0.6"
    best[("pr12EQ", "pr12EQBand1")] = "3"
    best[("parameters", "gateActive")] = "true"
    best[("parameters", "gateThreshold")] = "-40"
    best[("pr12Amp", "pr12Treble")] = "0.9"
    ab = F.ablation_settings(best, st, "pr12")
    assert set(ab) == set(F.ABLATIONS)
    p = ab["pedals_reset"]
    assert p[("drive1", "drive1Active")] == st[("drive1", "drive1Active")] and p[("pr12EQ", "pr12EQBand1")] == "3"
    e = ab["eq_reset"]
    assert e[("pr12EQ", "pr12EQBand1")] == st[("pr12EQ", "pr12EQBand1")] and e[("drive1", "drive1Drive")] == "0.6"
    b = ab["pedals_eq_reset"]
    assert b[("drive1", "drive1Active")] == st[("drive1", "drive1Active")] and b[("pr12EQ", "pr12EQBand1")] == st[
        ("pr12EQ", "pr12EQBand1")]
    gr = ab["gate_reset"]
    assert gr[("parameters", "gateActive")] == st[("parameters", "gateActive")] and gr[("drive1", "drive1Drive")] == "0.6"
    assert all(v[("pr12Amp", "pr12Treble")] == "0.9" for v in ab.values())  # the core knobs stay the best's


def test_incumbent_and_checkpoints():
    v = [5.0, 4.0, float("inf"), 4.0, 3.0, None, 3.5]
    assert F.incumbent_at(v, 1) == 0 and F.incumbent_at(v, 2) == 1 and F.incumbent_at(v, 4) == 1   # earliest on ties
    assert F.incumbent_at(v, 7) == 4 and F.incumbent_at([float("nan")], 1) is None
    cp = F.checkpoints(list(range(300, 0, -1)), 100)
    assert set(cp) == {50, 100} and cp[50] == 49 and cp[100] == 99
    assert set(F.checkpoints([1.0] * 10, 300)) == set(F.CHECKPOINTS)


def test_c2_budget_takes_the_first_checkpoint_reaching_ninety_percent_of_the_median():
    c = [{50: 0.5, 100: 0.8, 150: 0.92, 200: 0.95, 300: 1.0}, {50: 0.1, 100: 0.5, 150: 0.9, 200: 0.99, 300: 1.0},
         {50: 0.3, 100: 0.9, 150: 0.95, 200: 1.0, 300: 1.0}, {50: 0.0, 100: 0.0, 150: 0.0, 200: 0.0, 300: 0.0}]
    n, med = F.c2_budget(c)
    assert n == 150 and math.isclose(med[100], 0.8) and math.isclose(med[150], 0.92)
    assert F.c2_budget([{k: 0.0 for k in F.CHECKPOINTS}]) == (None, {})
    assert F.c2_budget(c, share=0.99)[0] == 200 and F.c2_budget(c, share=0.995)[0] == 300
    scaled = [{k: 2 * x for k, x in d.items()} for d in c]                    # ratios, not raw gains
    assert F.c2_budget(scaled)[0] == 150


def test_jackknife_mean_by_hand():
    pairs = [("a", 1.0), ("a", 3.0), ("b", 2.0), ("c", 6.0)]
    r = F.jackknife_mean(pairs)
    assert math.isclose(r["mean"], 3.0) and r["clusters"] == 3 and r["df"] == 2 and r["records"] == 4
    th = [(2 + 6) / 2, (1 + 3 + 6) / 3, (1 + 3 + 2) / 3]
    m = sum(th) / 3
    assert math.isclose(r["se"], math.sqrt(2 / 3 * sum((x - m) ** 2 for x in th)))
    one = F.jackknife_mean([("a", 1.0), ("a", 2.0)])
    assert one["se"] is None and math.isclose(one["mean"], 1.5)
    w = F.with_interval(r, lambda df: 2.0)
    assert math.isclose(w["lo"], 3.0 - 2 * r["se"]) and math.isclose(w["hi"], 3.0 + 2 * r["se"])
    assert F.with_interval(one, lambda df: 2.0)["lo"] is None


def searched(cluster, cls, label_h, new_h, s_h, abl=1.0, held="B"):
    j = lambda v: {"A": 9.0, "B": v} if held == "B" else {"A": v, "B": 9.0}          # noqa: E731
    return {"cluster": cluster, "unit": f"u-{cluster}", "cls": cls, "held": held, "label": {},
            "source_best_judge": j(label_h),
            "s_judge": j(s_h), "fresh": {"best": {"judge": j(new_h)},
                                          "ablations": {a: {"judge": j(new_h * abl)} for a in F.ABLATIONS}},
            "changed": {"drive1": True, "drive2": False, "compressor": False, "eq_moved_from_S": True, "gate": False}}


def test_report_rows_use_the_held_half_and_split_by_class():
    rs = [searched("d1", "clean", 4.0, 3.0, 5.0), searched("d2", "crunch", 4.0, 4.4, 5.0, abl=1.1),
          searched("d3", "clean", 2.0, 2.0, 2.5, held="A")]
    out = F.report_rows(rs, lambda df: 2.0, P.clustered)
    p = out["all"]["primary"]
    assert math.isclose(p["mean"], (math.log(0.75) + math.log(1.1) + 0.0) / 3) and p["clusters"] == 3
    assert math.isclose(out["clean"]["primary"]["mean"], math.log(0.75) / 2)
    assert math.isclose(out["crunch"]["primary"]["mean"], math.log(1.1)) and out["crunch"]["primary"]["se"] is None
    assert math.isclose(out["all"]["label_vs_S"]["mean"], (2 * math.log(0.8) + math.log(0.8)) / 3)
    assert math.isclose(out["crunch"]["ablations"]["gate_reset"]["mean"], math.log(1.1))
    assert out["all"]["changed_counts"] == {"drive1": 3, "drive2": 0, "compressor": 0, "eq_moved_from_S": 3, "gate": 0}
    nolabel = dict(rs[0], label=None)
    assert F.report_rows([nolabel], lambda df: 2.0, P.clustered)["records"] == 0
    bw = out["all"]["primary"]["band_weighted"]
    assert bw["clusters"] == 3 and set(bw["per_cluster"]) == {"d1", "d2", "d3"}
    assert math.isclose(bw["per_cluster"]["d2"], math.log(1.1))
    broken = dict(rs[0], fresh={"best": {"judge": {"A": 9.0, "B": float("nan")}}, "ablations": {}})
    assert F.report_rows([broken], lambda df: 2.0, P.clustered)["records"] == 0      # finite guard
    no_s = dict(rs[0], s_judge={"A": 9.0, "B": 0.0})
    assert F.report_rows([no_s], lambda df: 2.0, P.clustered)["records"] == 0


def test_changed_reads_switches_from_the_start_and_the_eq_from_s():
    st = full_start()
    S = dict(st)
    best = dict(st)
    best[("compressor", "compressorActive")] = "true"
    out = F.changed(best, st, "pr12", S)
    assert out == {"drive1": False, "drive2": False, "compressor": True, "eq_moved_from_S": False, "gate": False,
                   "drive1_knobs": False, "drive2_knobs": False, "compressor_knobs": False}
    st_on = dict(st)
    st_on[("drive1", "drive1Active")] = "true"
    moved = dict(st_on)
    moved[("drive1", "drive1Tone")] = "0.9"
    assert F.changed(moved, st_on, "pr12", S)["drive1_knobs"] and not F.changed(moved, st_on, "pr12", S)["drive1"]
    off = dict(st)
    off[("drive1", "drive1Tone")] = "0.9"                                       # an off pedal's knobs don't count
    assert not F.changed(off, st, "pr12", S)["drive1_knobs"]
    best[("pr12EQ", "pr12EQHpf")] = "80"
    best[("parameters", "gateActive")] = "true"
    out = F.changed(best, st, "pr12", S)
    assert out["eq_moved_from_S"] and out["gate"]
    S2 = dict(S)
    S2[("pr12EQ", "pr12EQActive")] = "false"                                 # the switch itself doesn't count
    assert F.changed(dict(st), st, "pr12", S2)["eq_moved_from_S"] is False
    S3 = dict(S)
    S3[("pr12EQ", "pr12EQBand5")] = "-6"                                        # the label's EQ already differs from S's
    assert F.changed(dict(st), st, "pr12", S3)["eq_moved_from_S"] is True


def test_the_search_is_a_render_command_and_the_rest_are_not():
    assert any(re.search(p, "python -u -m learn.full_controls c1a-search --shard 0/3") for p in LO.RENDERS)
    for cmd in ("c1a-draw", "c1a-report"):
        assert not any(re.search(p, f"python -m learn.full_controls {cmd}") for p in LO.RENDERS)


def test_the_budget_truncates_one_deterministic_search():
    """The subset's first 100 evaluations are its 100-budget run: `coord_search` only truncates."""
    dims = [K.Dim("m", f"k{i}", "cont") for i in range(6)]
    x0 = {(d.module, d.key): "0.5" for d in dims}
    target = [0.1, 0.9, 0.3, 0.7, 0.2, 0.8]

    def run(budget):
        seen = []

        def f(x):
            v = 1 + sum((float(x[(d.module, d.key)]) - t) ** 2 for d, t in zip(dims, target))
            seen.append(v)
            return v
        K.coord_search(dims, x0, f, budget, F.SEED, cats="levels")
        return seen

    long, short = run(60), run(25)
    assert len(short) == 25 and long[:25] == short


def test_audible_change_flags_a_key_outside_the_table():
    lab = full_start()
    st = dict(F.c1a_start(LO.sdict(lab), "pr12"))
    st[("nowhere", "unknownKey")] = "1"
    assert F.audible_change(st, LO.sdict(lab), "pr12", declared=F.GATE_KEYS) == ["nowhere/unknownKey"]


def test_c1a_space_refuses_a_categorical_dim(monkeypatch):
    monkeypatch.setattr(K2, "stage1_space", lambda amp, start: [K.Dim("cabParameters", "leftMicType", "cat", values=("0",))])
    with pytest.raises(SystemExit):
        F.c1a_space("pr12", full_start())


def test_amp_choice_value_is_the_chosen_held_half_against_the_mean_log():
    def r(h, held="B", label=True):
        return {"held": held, "best": {"judge": {"A": 1.0, "B": h} if held == "B" else {"A": h, "B": 1.0}},
                "label": {} if label else None}
    recs = {"pr12": r(2.0), "sw50r": r(4.0), "ac20": r(8.0, label=False)}
    assert math.isclose(F.amp_choice_value(recs, "pr12"), math.log(2.0) - (math.log(2.0) + math.log(4.0)) / 2)
    recs["ac20"] = r(8.0, held="A")
    assert math.isclose(F.amp_choice_value(recs, "sw50r"), math.log(4.0) - math.log(64.0) / 3)
    recs["pr12"] = r(float("inf"))                                               # finite guard
    assert math.isclose(F.amp_choice_value(recs, "sw50r"), math.log(4.0) - math.log(32.0) / 2)
    assert F.amp_choice_value(recs, "pr12") is None


def test_canon_gate_uses_the_declared_acting_value(monkeypatch):
    monkeypatch.setattr(F, "GATE_ON_DB", "-55")
    x = {("parameters", "gateActive"): "false", ("parameters", "gateThreshold"): "-12"}
    assert F.canon_gate(x)[("parameters", "gateThreshold")] == "-55"
    x[("parameters", "gateActive")] = "true"
    assert F.canon_gate(x)[("parameters", "gateThreshold")] == "-12"
    st = full_start()
    st[("parameters", "gateActive")] = "false"
    assert F.make_canon("pr12")(st)[("parameters", "gateThreshold")] == "-55"


def test_subset_curves_read_both_halves_from_the_checkpoints():
    r = {"subset": True, "search": "A", "held": "B", "trials": [{"judge": {"A": 4.0, "B": 5.0}}],
         "checkpoints": {"50": {"judge": {"A": 2.0, "B": 4.0}}, "300": {"judge": {"A": 1.0, "B": 5.0}}}}
    (c,) = F.subset_curves([r, dict(r, subset=False)])
    assert math.isclose(c["search"][50], math.log(2.0)) and math.isclose(c["search"][300], math.log(4.0))
    assert math.isclose(c["held"][50], math.log(5 / 4)) and c["held"][300] == 0.0


TARGET = {("pr12EQ", f"pr12EQBand{i + 1}"): t for i, t in enumerate((5, -7, 3, 9, -2, 6, -4, 8, 1))}


GATE_COST = {"v": 0.0}                                                          # a gate that acts, when set


def _value(x):
    gate = GATE_COST["v"] if str(x.get(("parameters", "gateActive"))).lower() == "true" else 0.0
    return 2.0 + sum((float(x[k]) - t) ** 2 for k, t in TARGET.items()) / 1000 + gate


def _stub(tmp_path, monkeypatch, recs, miss=(), src_amp="pr12", gate_cost=0.0, run_cost=0.0):
    """cmd_search on stub audio and a stub renderer whose judge reads the EQ's distance to TARGET."""
    import argparse  # noqa: F401
    np = pytest.importorskip("numpy")
    from learn import arm_a_levers as L
    from learn import audibility_measure as AM
    from learn import cc_build as CB
    from learn import pretrain_set as PS
    from learn import song_bank as B

    S = full_start("pr12")
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(P, "require", lambda k: {})
    monkeypatch.setattr(LO, "_wait_cap", lambda *a: None)
    monkeypatch.setattr(PS, "free_gb", lambda: 1e9)
    monkeypatch.setattr(PS, "TRIM_S", 0.0)
    monkeypatch.setattr(PS, "SEC_S", 1.0)
    monkeypatch.setattr(PS, "SR", 4)
    monkeypatch.setattr(PS, "section_audio", lambda path, start: np.zeros(4))
    monkeypatch.setattr(B, "measure", lambda a: np.zeros(4))
    monkeypatch.setattr(P, "real_amp_track", lambda sd, track, start: np.zeros(4))
    monkeypatch.setattr(L, "menu_S", lambda: {"pr12": {"clean": (0, S)}})
    calls = {"n": 0}

    class R:
        def render(self, di, sel, x):                                           # run_cost: in-process, gate off only
            calls["n"] += 1
            off = str(x.get(("parameters", "gateActive"))).lower() != "true"
            return np.full(4, _value(x) + (run_cost if off else 0.0))

        def close(self):
            pass

    def fresh(make, di, sel, xp, x):
        calls["n"] += 2
        return np.full(4, _value(x))
    monkeypatch.setattr(CB, "new_renderer", lambda: R())
    monkeypatch.setattr(AM, "fresh_render", fresh)
    monkeypatch.setattr(K, "judge", lambda ref, y, di, lag: {"A": float(y[0]), "B": float(y[0]) + 0.5})
    monkeypatch.setattr(F, "BUDGET", 10)
    monkeypatch.setattr(F, "SUBSET_BUDGET", 30)
    monkeypatch.setattr(F, "CHECKPOINTS", (5, 10, 20, 30))
    monkeypatch.setitem(GATE_COST, "v", gate_cost)
    label = LO.sdict(S)
    v0 = _value(S)                                                              # the stored label's own value
    rows = []
    for i, (st, subset) in enumerate(recs):
        unit = f"{'cap' if st == 'n12' else 'set5'}/u{i}"
        src = tmp_path / "src" / f"u{i}.json"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(json.dumps({"unit": unit, "amp": src_amp, "select": 0, "label": label, "search": "A", "held": "B",
                                   "lag": 0, "s_judge": {"A": 3.0, "B": 3.5}, "rig": "r", "di": "d",
                                   "best": {"settings": label, "judge": {"A": v0 * (1.1 if i in miss else 1.0), "B": v0 + 0.5},
                                            "render_sha256": "x"}}))
        rows.append({"set": st, "key": f"{unit}|pr12", "unit": unit, "amp": "pr12", "cls": "clean", "cluster": f"c{i}",
                     "source": str(src), "prt": {"di_path": "", "start_s": 0.0, "sd": "", "track": ""},
                     "real_out": False, "subset": subset, "budget": 30 if subset else 10})
    (tmp_path / "c1a").mkdir(exist_ok=True)
    (tmp_path / "c1a" / "records.json").write_text(json.dumps({"records": rows}))
    return rows, calls


def _out(tmp_path, r):
    root, sub = F.OUT_DIRS[r["set"]]
    return tmp_path / root / sub / f"{F.fname(r['key'])}.json"


def test_cmd_search_labels_resume_and_render_count(tmp_path, monkeypatch, capsys):
    import argparse
    rows, calls = _stub(tmp_path, monkeypatch, [("bks", True), ("n12", False), ("n12", False)])
    kept = _out(tmp_path, rows[2])
    kept.parent.mkdir(parents=True, exist_ok=True)
    kept.write_text('{"kept": true}')
    F.cmd_search(argparse.Namespace(shard=(0, 1)))
    assert json.loads(kept.read_text()) == {"kept": True}                        # resume: skipped
    sub, plain = (json.loads(_out(tmp_path, r).read_text()) for r in rows[:2])
    names = [d.name for d in F.c1a_space("pr12", F.c1a_start(LO.sdict(full_start("pr12")), "pr12"))]
    assert sub["searched_keys"] == names == plain["searched_keys"]
    assert sub["evaluations"] == 30 and plain["evaluations"] == 10
    i10, i30 = F.incumbent_at(sub["curve"], 10), F.incumbent_at(sub["curve"], 30)
    assert i10 != i30
    for lab, i in ((sub["label"], i10), (sub["label_300"], i30)):
        assert {k: lab[k] for k in names} == sub["trials"][i]["x"]
    assert {k: plain["label"][k] for k in names} == plain["trials"][F.incumbent_at(plain["curve"], 10)]["x"]
    assert sub["start_settings"] and plain["measurement_only"] and not sub["measurement_only"]
    assert sub["start_settings"]["parameters/gateActive"] == "true"               # the start has the gate on
    assert sub["start_settings"]["parameters/gateThreshold"] == F.GATE_ON_DB
    assert sub["fresh"]["ablations"]["pedals_reset"]["same_as_best"]                 # nothing to reset: reused
    assert not sub["fresh"]["ablations"]["eq_reset"]["same_as_best"]
    assert not sub["fresh"]["best_300"]["same_as_best"]                          # a different best: rendered fresh
    assert sub["fresh"]["best_300"]["judge"] == sub["trials"][i30]["judge"]
    assert sub["fresh"]["best"]["judge"] == sub["trials"][i10]["judge"]
    want = sum(1 + r["evaluations"] + 2 * (1 + sum(not a["same_as_best"] for a in r["fresh"]["ablations"].values())
                                          + (0 if "best_300" not in r["fresh"] or r["fresh"]["best_300"]["same_as_best"]
                                             else 1)) for r in (sub, plain))
    assert f"C1A-SEARCH DONE 0/1: {want} renders" in capsys.readouterr().out and calls["n"] == want


def test_cmd_search_refuses_a_miss_the_gate_does_not_explain_and_continues(tmp_path, monkeypatch, capsys):
    import argparse
    rows, calls = _stub(tmp_path, monkeypatch, [("n12", False), ("n12", False)], miss={0})
    F.cmd_search(argparse.Namespace(shard=(0, 1)))
    bad, good = (json.loads(_out(tmp_path, r).read_text()) for r in rows)
    assert bad["start_gate"] == "refused" and bad["label"] is None and "trials" not in bad
    ref = bad["refused"]["ref_value"]
    assert not F.within(bad["refused"]["value"], ref) and not F.within(bad["refused"]["gate_off_value"], ref)
    assert good["start_gate"] == "on" and good["first_start_miss"] is None and good["label"] is not None
    out = capsys.readouterr().out
    assert "starts {'on': 1, 'off_after_miss': 0, 'refused': 1}" in out
    want = 2 + 2 + (1 + good["evaluations"] + 2 * (1 + sum(not a["same_as_best"]
                                                           for a in good["fresh"]["ablations"].values())))
    assert f"C1A-SEARCH DONE 0/1: {want} renders" in out and calls["n"] == want
    assert F.start_counts([bad, good, {"x": 1}]) == {"on": 2, "off_after_miss": 0, "refused": 1}
    F.cmd_search(argparse.Namespace(shard=(0, 1)))                                # resume: both written, skipped
    assert "C1A-SEARCH DONE 0/1: 0 renders" in capsys.readouterr().out


def test_cmd_search_restarts_from_the_gate_off_when_the_gate_alone_missed(tmp_path, monkeypatch, capsys):
    import argparse
    rows, calls = _stub(tmp_path, monkeypatch, [("bks", False)], gate_cost=0.1)
    F.cmd_search(argparse.Namespace(shard=(0, 1)))
    r = json.loads(_out(tmp_path, rows[0]).read_text())
    assert r["start_gate"] == "off_after_miss" and r["label"] is not None
    assert r["start_settings"]["parameters/gateActive"] == "false"
    assert r["start_settings"]["parameters/gateThreshold"] == F.GATE_ON_DB             # canonical while off
    assert "parameters/gateActive" in r["searched_keys"] and "parameters/gateThreshold" in r["searched_keys"]
    m = r["first_start_miss"]
    assert not F.within(m["value"], m["ref_value"]) and F.within(m["gate_off_value"], m["ref_value"])
    assert F.within(r["start"]["value"], r["start"]["ref_value"])
    assert "gate_off_sha" in m and "gate_off_bit_identical" in m and "gate_off_run_value" not in m
    assert r["ledger"].endswith(F.PHASE_A1) and F.PHASE in r["ledger"]
    out = capsys.readouterr().out
    assert "starts {'on': 0, 'off_after_miss': 1, 'refused': 0}" in out
    want = 2 + 2 + 1 + r["evaluations"] + 2 * (1 + sum(not a["same_as_best"] for a in r["fresh"]["ablations"].values()))
    assert f"C1A-SEARCH DONE 0/1: {want} renders" in out and calls["n"] == want
    assert r["fresh"]["ablations"]["gate_reset"]["same_as_best"]                    # the gate stays as the start's: off


def test_start_plan_and_within():
    assert F.start_plan(True, None) == "on" and F.start_plan(False, True) == "off_after_miss"
    assert F.start_plan(False, False) == "refused" and F.start_plan(False, None) == "refused"
    assert F.within(1.004, 1.0) and not F.within(1.006, 1.0) and not F.within(float("nan"), 1.0)
    assert not F.within(0.0, 1.0) and F.within(math.exp(-0.0049), 1.0) and not F.within(math.exp(-0.0051), 1.0)


def test_cmd_search_refuses_a_source_of_another_amp(tmp_path, monkeypatch):
    import argparse
    _stub(tmp_path, monkeypatch, [("n12", False)], src_amp="sw50r")
    with pytest.raises(SystemExit, match="does not fit"):
        F.cmd_search(argparse.Namespace(shard=(0, 1)))


def test_split_refused_keeps_the_searched_records_and_lists_the_refused():
    done = {"unit": "a", "label": {}}
    bad = {"unit": "b", "set": "n12", "amp": "ac20", "cls": "clean", "subset": True, "real_out": False, "label": None,
           "refused": {"value": 1.0, "ref_value": 2.0}}
    recs, refused = F.split_refused([done, bad])
    assert recs == [done] and refused == [{"unit": "b", "set": "n12", "amp": "ac20", "cls": "clean", "subset": True,
                                           "real_out": False, "value": 1.0, "ref_value": 2.0}]


def test_cmd_search_needs_the_amendments_ledger_entry(tmp_path, monkeypatch):
    import argparse
    _stub(tmp_path, monkeypatch, [("n12", False)])

    def require(k):
        if k == F.PHASE_A1:
            raise SystemExit(f"no {k}")
        return {}
    monkeypatch.setattr(P, "require", require)
    with pytest.raises(SystemExit, match="phase_c1a_a1"):
        F.cmd_search(argparse.Namespace(shard=(0, 1)))


def test_cmd_search_refuses_when_the_gate_off_run_misses_after_a_matching_fresh_start(tmp_path, monkeypatch, capsys):
    import argparse
    rows, calls = _stub(tmp_path, monkeypatch, [("n12", False), ("n12", False)], gate_cost=0.1, run_cost=0.05)
    F.cmd_search(argparse.Namespace(shard=(0, 1)))
    for r in rows:
        got = json.loads(_out(tmp_path, r).read_text())
        assert got["start_gate"] == "refused" and got["label"] is None and "trials" not in got
        m = got["refused"]
        assert F.within(m["gate_off_value"], m["ref_value"]) and not F.within(m["gate_off_run_value"], m["ref_value"])
    out = capsys.readouterr().out
    assert "starts {'on': 0, 'off_after_miss': 0, 'refused': 2}" in out
    assert "C1A-SEARCH DONE 0/1: 12 renders" in out and calls["n"] == 12              # 2 + 2 + 2 a record


def test_gate_rows_split_the_two_meanings_of_the_gate_ablation():
    on = searched("d1", "clean", 4.0, 3.0, 5.0)
    off = dict(searched("d2", "clean", 4.0, 3.6, 5.0, abl=1.2), start_gate="off_after_miss",
               best={"settings": {"parameters/gateActive": "true", "parameters/gateThreshold": "-55"}},
               start_settings={"parameters/gateActive": "false", "parameters/gateThreshold": "-80"}, set="n12")
    assert F.gate_on_start(on) and not F.gate_on_start(off) and F.gate_on_start(dict(on, start_gate="on"))
    (row,) = F.gate_off_rows([on, off])
    assert row["unit"] == "u-d2" and math.isclose(row["primary"], math.log(0.9))
    assert math.isclose(row["gate_reset"], math.log(1.2)) and row["gate"] == "turned on, threshold moved"
    stay = dict(off, best={"settings": {"parameters/gateActive": "false", "parameters/gateThreshold": "-80"}})
    assert F.gate_off_rows([stay])[0]["gate"] == "stayed off"


def test_start_against_the_label_reads_the_stored_first_trial():
    r = dict(searched("d1", "clean", 4.0, 3.0, 5.0), trials=[{"judge": {"A": 9.0, "B": 4.02}}])
    v = F.record_values(r)
    assert math.isclose(v["start_vs_label"], math.log(4.02 / 4.0))
    out = F.report_rows([r], lambda df: 2.0, P.clustered)
    assert math.isclose(out["all"]["start_vs_label"]["mean"], math.log(4.02 / 4.0))
    assert "start_vs_label" not in F.record_values(searched("d1", "clean", 4.0, 3.0, 5.0))


def test_cmd_report_gives_gate_on_rows_beside_the_pooled_and_counts_the_starts(tmp_path, monkeypatch, capsys):
    pytest.importorskip("scipy")
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(P, "require", lambda k: {})
    d = tmp_path / "captures2" / "search-c1a"
    d.mkdir(parents=True)
    base = dict(real_out=False, subset=False, start={"bit_identical": True}, set="n12")
    on1 = dict(searched("b1", "clean", 4.0, 3.0, 5.0), **base, unit="u1",
               best={"settings": {"parameters/gateActive": "true", "parameters/gateThreshold": "-55"}})
    on2 = dict(searched("b2", "clean", 4.0, 3.4, 5.0), **base, unit="u2")
    off = dict(searched("b3", "crunch", 4.0, 2.0, 5.0), **base, unit="u3", start_gate="off_after_miss",
               best={"settings": {"parameters/gateActive": "false"}}, start_settings={})
    bad = {"unit": "u4", "set": "n12", "label": None, "real_out": False, "subset": False, "start_gate": "refused",
           "refused": {"value": 1.0, "ref_value": 2.0, "gate_off_value": 1.5}}
    for i, r in enumerate((on1, on2, off, bad)):
        (d / f"r{i}.json").write_text(json.dumps(r))
    (tmp_path / "c1a").mkdir()
    (tmp_path / "c1a" / "records.json").write_text(json.dumps({"records": []}))
    F.cmd_report(None)
    rep = json.loads((tmp_path / "c1a" / "report.json").read_text())["n12"]
    assert rep["starts"] == {"on": 2, "off_after_miss": 1, "refused": 1}
    assert rep["rows"]["records"] == 3 and rep["rows_gate_on_start"]["records"] == 2
    assert math.isclose(rep["rows_gate_on_start"]["all"]["primary"]["mean"], (math.log(0.75) + math.log(0.85)) / 2)
    assert [g["unit"] for g in rep["gate_off_after_miss"]] == ["u3"] and rep["refused"][0]["unit"] == "u4"
    assert rep["gate_threshold_moved_on"] == 1 and "subset_median_gain" in rep and set(rep["subset_median_gain"]) == {
        "search", "held"}
    printed = json.loads(capsys.readouterr().out.split("C2 budget")[0])["n12"]
    assert printed["refused"] == 1 and printed["starts"] == {"on": 2, "off_after_miss": 1, "refused": 1}


def test_factory_guard_refuses_no_gate_on_or_another_median():
    F.factory_guard(-80.0, 107, 102)
    with pytest.raises(SystemExit):
        F.factory_guard(F.GATE_FALLBACK_DB, 107, 0)                                # none on: refused, not the fallback
    with pytest.raises(SystemExit):
        F.factory_guard(-80.0, 107, 0)
    with pytest.raises(SystemExit):
        F.factory_guard(-70.0, 107, 102)


def test_gate_threshold_moved_counts_only_an_on_gate_off_the_factory_value():
    def rec(active, thr):
        return {"best": {"settings": {"parameters/gateActive": active, "parameters/gateThreshold": thr}}}
    assert F.gate_threshold_moved(rec("true", "-55"))
    assert not F.gate_threshold_moved(rec("true", F.GATE_ON_DB)) and not F.gate_threshold_moved(rec("true", "-80.0"))
    assert not F.gate_threshold_moved(rec("false", "-55")) and not F.gate_threshold_moved({})


def test_median_gain_keeps_losers():
    cur = [{"held": {50: -0.02, 300: 0.01}}, {"held": {50: -0.04, 300: -0.03}}, {"held": {50: 0.01}}]
    got = F.median_gain(cur, "held")
    assert math.isclose(got[50], -0.02) and math.isclose(got[300], (0.01 - 0.03) / 2) and 100 not in got


def test_gate_off_rows_carry_real_out():
    off = dict(searched("d2", "clean", 4.0, 3.6, 5.0), start_gate="off_after_miss", real_out=True,
               best={"settings": {"parameters/gateActive": "false"}}, start_settings={})
    assert F.gate_off_rows([off])[0]["real_out"] is True
    assert F.gate_off_rows([dict(off, real_out=False)])[0]["real_out"] is False


def test_cmd_draw_checks_the_factory_gate_before_it_writes(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(P, "out_dir", lambda root=None: tmp_path)
    monkeypatch.setattr(P, "require", lambda k: {})
    recs = [{"set": "n12", "key": f"n{i}", "unit": f"n{i}"} for i in range(8)] + [
        {"set": "bks", "key": f"b{i}", "unit": f"b{i}"} for i in range(8)]
    monkeypatch.setattr(F, "load_sources", lambda: [dict(r) for r in recs])
    monkeypatch.setattr(F, "factory_gate_median", lambda: (-70.0, 107, 102))
    with pytest.raises(SystemExit, match="factory gate median"):
        F.cmd_draw(None)
    assert not (tmp_path / "c1a" / "records.json").exists()
    monkeypatch.setattr(F, "factory_gate_median", lambda: (-80.0, 107, 102))
    F.cmd_draw(None)
    got = json.loads((tmp_path / "c1a" / "records.json").read_text())
    assert got["gate_factory"] == {"median_db": -80.0, "presets": 107, "gate_on": 102, "used": F.GATE_ON_DB}
    assert sum(r["subset"] for r in got["records"]) == 12
    assert all(r["measurement_only"] == (r["set"] == "n12") for r in got["records"])
