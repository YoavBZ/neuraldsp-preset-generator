"""The note-matched replay's pure parts (`learn/note_replay.py`, `docs/note-replay-plan.md`): the menu rule, the draw,
the picks, the part's numbers, the readings, R_TABLE, the dry-guitar reading, the Both notes, the Control's check, the
position mode and the refusals. Pure: runs on the light CI runner (no numpy)."""
import itertools
import math
import random

import pytest

from learn import note_replay as N


def _iv(mean, lo, hi):
    return {"mean": mean, "lo90": lo, "hi90": hi}


# --- the menu rule ---------------------------------------------------------------------------------------------------------

def test_level_menu_takes_the_nearest_trial_to_each_level_best_first():
    ln = [float(i) for i in range(40)]                  # levels 0, 39/19, ...: each nearest distinct trial
    got = N.level_menu(ln, 20)
    assert got == [round(39 * j / 19 + 1e-9) if j else 0 for j in range(20)]
    assert N.level_menu(list(reversed(ln)), 20)[0] == 39


def test_level_menu_breaks_a_tie_to_the_lower_position_and_never_takes_twice():
    ln = [0.0, 0.0, 1.0, 1.0] + [0.5] * 20
    got = N.level_menu(ln, 20)
    assert got[0] == 0 and 1 in got and len(set(got)) == 20


def test_level_menu_refuses_too_few_trials():
    with pytest.raises(SystemExit):
        N.level_menu([0.1] * 19, 20)


def _judges(rng, n, both=True):
    return [{"A": math.exp(rng.uniform(1, 2)), "B": math.exp(rng.uniform(1, 2)) if both else None} for _ in range(n)]


def _fixed(rng):
    return {k: (1, {f"{k}/x": 0.5}, {"A": math.exp(rng.uniform(1, 2)), "B": math.exp(rng.uniform(1, 2))})
            for k in N.FIXED}


def test_menu_order_and_size():
    rng = random.Random(1)
    trials = [(i, {"m/k": i}, j) for i, j in enumerate(_judges(rng, 60))]
    menu, why = N.menu_of(_fixed(rng), trials, "A", "B")
    assert why is None and len(menu) == N.MENU_N == 23
    assert [m["kind"] for m in menu[:3]] == ["cen", "S", "label"] and all(m["kind"] == "step1" for m in menu[3:])
    s = [m["stored_search"] for m in menu[3:]]
    assert s[0] == min(t[2]["A"] for t in trials) and s[-1] == max(t[2]["A"] for t in trials)


def test_menu_reads_held_finiteness_only():
    """The halves never mix: with every held-half value replaced by noise (finite), the menus are unchanged."""
    rng = random.Random(2)
    fx = _fixed(rng)
    trials = [(i, {"m/k": i}, j) for i, j in enumerate(_judges(rng, 80))]
    menu, _ = N.menu_of(fx, trials, "A", "B")
    noise = random.Random(99)
    fx2 = {k: (a, b, {"A": j["A"], "B": math.exp(noise.gauss(0, 3))}) for k, (a, b, j) in fx.items()}
    t2 = [(i, x, {"A": j["A"], "B": math.exp(noise.gauss(0, 3))}) for i, x, j in trials]
    assert N.menu_of(fx2, t2, "A", "B")[0] == menu


def test_menu_passes_over_a_trial_without_a_finite_held_half_and_refuses_a_thin_part():
    rng = random.Random(3)
    j = _judges(rng, 25)
    for x in j[:6]:
        x["B"] = math.inf
    trials = [(i, {}, x) for i, x in enumerate(j)]
    menu, why = N.menu_of(_fixed(rng), trials, "A", "B")
    assert menu is None and "19 usable" in why
    j2 = _judges(rng, 30)
    j2[0]["B"] = math.inf
    menu, why = N.menu_of(_fixed(rng), [(i, {}, x) for i, x in enumerate(j2)], "A", "B")
    assert why is None and all(m["index"] != 0 for m in menu[3:])


def test_part_refusal_needs_cen_s_and_the_label_finite():
    assert N.part_refusal(20, {"cen": True, "S": True, "label": True}) is None
    assert "label" in N.part_refusal(53, {"cen": True, "S": True, "label": False})
    assert "fewer" in N.part_refusal(19, {"cen": True, "S": True, "label": True})


# --- the draw ----------------------------------------------------------------------------------------------------------------

def _cands(seed=0, refuse=()):
    rng = random.Random(seed)
    out = []
    for d in range(8):                                  # BKS: 8 DI files, 5 units each, 3 amps
        for u in range(5):
            for a in N.AMPS:
                out.append({"set": "bks", "unit": f"b{d}-{u}", "amp": a, "cluster": f"di{d}", "fold": d % 4,
                            "cls": "clean" if d < 4 else "crunch", "title": None, "ok": True})
    for t, n in (("RAW_05_02", 3), ("RAW_03_08", 1), ("Drowning", 3), ("Silent Waves", 2), ("ElecGtr01", 3)):
        for u in range(n):
            out.append({"set": "panel", "unit": f"p-{t}-{u}", "amp": N.AMPS[u % 3], "cluster": t, "fold": u % 4,
                        "cls": "clean", "title": t, "ok": True})
    for i in range(130):                                # GOAT: items over 4 folds, 2 renders an item
        for r in range(2):
            out.append({"set": "goat", "unit": f"g{i}#{r}", "amp": N.AMPS[(i + r) % 3], "cluster": f"item{i}",
                        "fold": i % 4, "cls": "clean" if (i // 4) % 2 else "crunch", "title": None, "ok": True})
    for c in out:
        if (c["set"], c["unit"], c["amp"]) in refuse:
            c["ok"] = False
    rng.shuffle(out)
    return out


def test_the_draw_is_the_declared_shape():
    c = _cands()
    res = N.draw_parts(c)
    by = {}
    for k in res["drawn"]:
        by.setdefault(k[0], []).append(k)
    assert len(by["bks"]) == 40 and len({u for _, u, _ in by["bks"]}) == 40       # one amp a unit
    assert len(by["panel"]) == 10 and res["excluded"] == 2
    assert len(by["goat"]) == 72
    meta = {(x["set"], x["unit"], x["amp"]): x for x in c}
    for f in range(4):
        g = [meta[k] for k in by["goat"] if meta[k]["fold"] == f]
        assert sum(x["cls"] == "clean" for x in g) == 9 and len({x["cluster"] for x in g}) == len(g)
    for d in range(8):                                  # the amps rotate inside a DI file
        amps = [a for _, u, a in by["bks"] if u.startswith(f"b{d}-")]
        assert sorted(amps.count(a) for a in N.AMPS) in ([1, 2, 2], [2, 2, 1], [1, 2, 2])
    assert N.draw_shortfall(res["drawn"], c) == []


def test_the_draw_is_seeded_and_order_free():
    a = N.draw_parts(_cands(0))
    b = N.draw_parts(_cands(5))                         # the same candidates in another order
    assert a == b
    assert N.draw_parts(_cands(0), seed=N.SEED + 1)["drawn"] != a["drawn"]


def test_a_refused_goat_part_is_passed_over_and_a_refused_bks_part_dropped():
    base = N.draw_parts(_cands())
    g = next(k for k in base["drawn"] if k[0] == "goat")
    b = next(k for k in base["drawn"] if k[0] == "bks")
    res = N.draw_parts(_cands(refuse={g, b}))
    assert g not in res["drawn"] and b not in res["drawn"]
    assert sum(k[0] == "goat" for k in res["drawn"]) == 72 and res["passed_over"] >= 1
    assert sum(k[0] == "bks" for k in res["drawn"]) == 39 and len(res["dropped"]) == 1


def test_the_draw_refuses_a_short_set():
    c = [x for x in _cands() if not (x["set"] == "goat" and x["fold"] == 0 and x["cls"] == "clean")]
    res = N.draw_parts(c)
    assert any("GOAT fold 0 clean" in s for s in N.draw_shortfall(res["drawn"], c))
    c2 = [x for x in _cands() if not (x["set"] == "panel" and x["title"] in ("RAW_03_08", "ElecGtr01"))]
    assert any("panel" in s for s in N.draw_shortfall(N.draw_parts(c2)["drawn"], c2))


def test_position_parts_four_a_set_never_the_bleed_check():
    keys = [(k[0], k[1], k[2], "Drowning" if "Drowning" in k[1] else None) for k in N.draw_parts(_cands())["drawn"]]
    got = N.position_parts(keys)
    assert len(got) == 12 and all(sum(k[0] == s for k in got) == 4 for s in N.SETS)
    assert not any("Drowning" in k[1] for k in got)
    assert N.position_parts(keys) == got


def test_others_come_from_every_other_source_at_most_eight_each():
    parts = [{"pkey": f"p{i}", "source": f"s{i % 4}", "section": f"sec{i}"} for i in range(60)]
    got = N.others_for(parts[0], parts)
    assert set(got) == {"s1", "s2", "s3"} and all(len(v) == 8 for v in got.values())
    assert got == N.others_for(parts[0], list(reversed(parts)))


# --- the picks and the numbers ---------------------------------------------------------------------------------------------

def test_pick_passes_over_non_finite_and_breaks_ties_low():
    assert N.pick_index([math.inf, 2.0, 1.0, 1.0]) == 2
    assert N.pick_index([None, math.nan, math.inf]) is None
    assert N.pick_index([1.0, 2.0, 0.5], skip=(2,)) == 0


def test_part_numbers():
    h = [0.0, 0.2] + [-0.3] + [0.1 * j for j in range(20)]
    d = [5.0] * 23
    d[2] = 1.0                                          # the label is the closest
    got = N.part_numbers(d, h)
    blind = sum(h) / 23
    assert got["pick"] == 2 and got["label_pick"] and got["G"] == -0.3
    assert got["I"] == pytest.approx(-0.3 - blind)
    rest = [v for j, v in enumerate(h) if j != 2]
    assert got["pick_nl"] == 0 and got["G_nl"] == 0.0 and got["I_nl"] == pytest.approx(0.0 - sum(rest) / 22)
    assert got["best"] == -0.3
    assert N.part_numbers([math.inf] * 23, h) is None


def test_the_picks_read_no_held_value():
    """With the held-half scores replaced by noise, the picks are unchanged (only the numbers move)."""
    rng = random.Random(7)
    d = [rng.uniform(1, 5) for _ in range(23)]
    h1 = [0.0] + [rng.gauss(0, 1) for _ in range(22)]
    h2 = [0.0] + [rng.gauss(0, 1) for _ in range(22)]
    a, b = N.part_numbers(d, h1), N.part_numbers(d, h2)
    assert (a["pick"], a["pick_nl"]) == (b["pick"], b["pick_nl"])


def test_spearman():
    assert N.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert N.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert N.spearman([1, 2, math.inf, 4, 5], [1, 2, 9, 3, 5]) == pytest.approx(1.0)
    assert N.spearman([1, 1, 1], [1, 2, 3]) is None
    assert N.spearman([1, 2], [1, 2]) is None


# --- the readings and the table -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("row,want", [
    (_iv(-0.12, -0.20, -0.04), "passes"),
    (_iv(-0.10, -0.15, -0.05), "passes"),
    (_iv(-0.09, -0.15, -0.03), "undecided"),       # decided better, but the mean short of -0.10
    (_iv(-0.12, -0.25, +0.01), "undecided"),       # the mean far enough, the interval reaching zero
    (_iv(+0.00, -0.05, +0.05), "fails"),           # a gain beyond -0.05 ruled out
    (_iv(+0.03, -0.04, +0.10), "fails"),
    (_iv(-0.02, -0.06, +0.02), "undecided"),
    (None, None)])
def test_number_reading(row, want):
    assert N.number_reading(row) == want


def test_unreadable():
    assert N.unreadable(_iv(0.0, -0.04, 0.05)) and not N.unreadable(_iv(0.0, -0.06, 0.04))


def test_row_reading_needs_both_numbers():
    p, u, f = _iv(-0.2, -0.3, -0.12), _iv(-0.08, -0.2, 0.01), _iv(0.0, -0.04, 0.04)
    assert N.row_reading(p, p)["reading"] == "passes"
    assert N.row_reading(p, u)["reading"] == "undecided"
    assert N.row_reading(p, f)["reading"] == "fails"           # G passes against Cen, but no better than blind
    assert N.row_reading(f, p)["reading"] == "fails"
    assert N.row_reading(u, u)["reading"] == "undecided"
    assert N.row_reading(p, None) is None
    assert N.row_reading(p, f)["I_not_readable"]


def test_r_table_is_whole_as_declared():
    N.table_guard()
    want = {}
    for d, a, f in itertools.product(N.READINGS, repeat=3):
        if d == "fails":
            want[(d, a, f)] = "R-dry"
        elif d == "undecided":
            want[(d, a, f)] = "R-undecided"
        elif a == "fails":
            want[(d, a, f)] = "R-stem"
        elif a == "undecided":
            want[(d, a, f)] = "R-undecided"
        else:
            want[(d, a, f)] = {"fails": "R-alone", "passes": "R-dry-only", "undecided": "R-undecided"}[f]
    assert {k: N.r_cell(*k)[0] for k in want} == want


@pytest.mark.parametrize("cut", [slice(0, -1), slice(1, None)])
def test_the_guard_refuses_a_broken_table(monkeypatch, cut):
    monkeypatch.setattr(N, "R_TABLE", N.R_TABLE[cut])
    with pytest.raises(SystemExit):
        N.table_guard()


def test_the_wording_and_the_pass_cells_next():
    assert "a dry guitar this degraded does not work" in N.R_CODES["R-dry"][0]
    assert "no route" not in " ".join(" ".join(v) for v in N.R_CODES.values())
    for c in ("R-alone", "R-dry-only"):
        nxt = N.R_CODES[c][1]
        assert "from-scratch search" in nxt and "necessary, not sufficient" in nxt and "held half" in nxt


@pytest.mark.parametrize("args,want", [
    (("passes",), ("passes", "avg+mild")),
    (("fails",), (None, "singles pending")),
    (("undecided",), (None, "singles pending")),
    (("fails", "passes", "fails"), ("passes", "avg")),
    (("undecided", "undecided", "passes"), ("passes", "mild")),
    (("undecided", "passes", "passes"), ("passes", "avg, mild")),
    (("fails", "fails", "fails"), ("fails", None)),
    (("undecided", "fails", "fails"), ("fails", None)),
    (("fails", "fails", "undecided"), ("undecided", None))])
def test_dry_reading(args, want):
    assert N.dry_reading(*args) == want


def _main(**kw):
    r = {"control": "passes", "blurred": "passes", "stem-alone": "passes", "stem-full": "passes",
         "both-alone": "passes", "both-full": "passes"}
    r.update(kw)
    return r


def test_outcome_triggers_the_singles_on_fails_or_undecided():
    for b in N.TRIGGER:
        got = N.outcome(_main(blurred=b))
        assert got["code"] == "singles-triggered" and "1 h 26 min to 2 h 46 min" in got["next"]
    assert N.outcome(_main())["code"] == "R-dry-only"


def test_outcome_after_the_singles():
    got = N.outcome(_main(blurred="undecided"), {"avg-only": "passes", "mild-only": "fails"})
    assert got["code"] == "R-dry-only" and "avg alone" in got["reading"]
    got = N.outcome(_main(blurred="fails", **{"stem-alone": "fails"}), {"avg-only": "fails", "mild-only": "fails"})
    assert got["code"] == "R-dry"
    got = N.outcome(_main(blurred="fails"), {"avg-only": "undecided", "mild-only": "fails"})
    assert got["code"] == "R-undecided"


def test_outcome_refuses_a_missing_reading():
    assert N.outcome(_main(**{"stem-full": None}))["code"] == "incomplete"
    assert N.outcome(_main(blurred="fails"), {"avg-only": "passes"})["code"] == "incomplete"


def test_both_rows_that_fail_or_read_undecided_are_reported():
    got = N.outcome(_main(**{"stem-full": "fails", "both-alone": "undecided"}))
    assert got["code"] == "R-alone" and len(got["both_notes"]) == 1 and "undecided" in got["both_notes"][0]
    got = N.outcome(_main(**{"both-alone": "fails", "both-full": "undecided"}))
    assert got["code"] == "R-dry-only" and len(got["both_notes"]) == 2
    assert N.outcome(_main())["both_notes"] == []
    got = N.outcome(_main(blurred="fails"), {"avg-only": "passes", "mild-only": "fails",
                                             "avg-both-alone": "fails", "avg-both-full": "passes"})
    assert len(got["both_notes"]) == 1 and got["both_notes"][0].startswith("avg-both-alone")
    assert N.both_notes("R-stem", {"both-alone": "fails"}) == []


# --- the Control, the position check, the refusals ------------------------------------------------------------------------

def _ctl(n_parts=10, dev=0.0, swap=False):
    parts = {}
    for i in range(n_parts):
        s = [1.0 + 0.1 * j for j in range(23)]
        r = [x * math.exp(dev) for x in s]
        if swap and i == 0:
            r[0], r[1] = r[1], r[0]
        parts[f"p{i}"] = (r, s)
    return parts


def test_control_check():
    assert N.control_check(_ctl())["ok"]
    assert N.control_check(_ctl(dev=0.004))["ok"]
    got = N.control_check(_ctl(dev=0.006))
    assert not got["ok"] and got["within_tol"] == 0
    got = N.control_check(_ctl(swap=True))                       # a large swap: beyond 0.02, and the order moves
    assert not got["ok"] and got["order_mismatches"] and got["beyond_max"]
    parts = _ctl()
    parts["p0"][0][5] = math.inf
    assert not N.control_check(parts)["ok"]


def test_the_order_check_skips_a_near_tie():
    s = [1.0, 1.005] + [2.0] * 21
    r = [1.0021, 1.002] + [2.0] * 21                            # within 0.005, pick flips on a near tie
    got = N.control_check({"p": (r, s)})
    assert got["ok"] and got["order_parts_gated"] == 0


def test_position_mode():
    assert N.position_mode([0.0, 0.004]) == "process"
    assert N.position_mode([0.0, 0.006]) == "fresh"
    assert N.position_mode([0.0, None]) == "fresh"
    assert N.position_mode([]) == "fresh"


def test_hash_refusal():
    e = {N.PHASE_PICKS: {"sha256": "abc"}}
    assert N.hash_refusal(e, N.PHASE_PICKS, "abc") is None
    assert "not the ledger's" in N.hash_refusal(e, N.PHASE_PICKS, "abd")
    assert "has no" in N.hash_refusal({}, N.PHASE_PICKS, "abc")


def test_bleed_check_enters_only_on_a_recorded_clean_verdict():
    assert N.bleed_included({"verdict": "clean"})
    assert not N.bleed_included({"verdict": "bleed"}) and not N.bleed_included(None)


def test_separation_running():
    ps = [(1, "python -m learn.note_replay sep --device mps"), (2, "python -m learn.note_replay render"),
          (3, "python -m learn.preset_ladder sep --rows xl@-3")]
    assert N.separation_running(ps, {9}) == [1, 3]
    assert N.separation_running(ps, {1, 3}) == []


def test_the_rows_are_declared():
    assert N.ROWS["control"] == ("true", "clean") and N.ROWS["blurred"] == ("avg+mild", "clean")
    assert N.ROWS["stem-alone"] == ("true", "xlnoG") and N.ROWS["stem-full"] == ("true", "xl")
    assert set(N.SINGLE_ROWS) >= {"avg-only", "mild-only"}
    assert N.MENU_N == 23 and N.LABEL_INDEX == 2
