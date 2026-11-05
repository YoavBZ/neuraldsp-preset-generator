"""N1 to N3's pure parts (`learn/night2.py`)."""
import pytest

from learn import night2 as N


def menu_s():
    from learn import arm_a_levers as L

    try:
        return L.menu_S()
    except FileNotFoundError:
        pytest.skip("needs the local S menu")


class D:
    def __init__(self, key, kind="cont", lo=0.0, hi=1.0, values=()):
        self.module, self.key, self.kind, self.lo, self.hi, self.values = "m", key, kind, lo, hi, values

    def from_unit(self, u):
        return self.lo + u * (self.hi - self.lo)


def test_groups():
    assert N.group("inputGain") == "drive" and N.group("ac20Power") == "drive"
    assert N.group("sw50rTreble") == "tone" and N.group("leftCabPosition") == "cab" and N.group("leftMicType") == "mic"


def test_replicate_pairs_need_half_b_then_half_a_five_seconds_on_and_one_amp_each():
    recs = []
    for amp in ("pr12", "ac20", "sw50r"):
        recs += [{"unit": "di@15.0#rig", "rig": "rig", "amp": amp, "search": "B"},
                 {"unit": "di@20.0#rig", "rig": "rig", "amp": amp, "search": "A"},
                 {"unit": "di@40.0#rig", "rig": "rig", "amp": amp, "search": "B"}]
    got = N.replicate_pairs(recs)
    assert len(got) == 1 and got[0][0]["unit"] == "di@15.0#rig" and got[0][1]["unit"] == "di@20.0#rig"
    assert got[0][0]["amp"] == got[0][1]["amp"]


def test_search_v2_keeps_only_real_gains_and_its_budget():
    dims = [D("inputGain"), D("ac20Cut"), D("leftCabPosition"), D("leftMicType", kind="cat")]
    x0 = {("m", "inputGain"): "0.5", ("m", "ac20Cut"): "0.5", ("m", "leftCabPosition"): "0.5", ("m", "leftMicType"): "1"}
    calls = []

    def f(x):
        calls.append(x)
        return 1.0 + (float(x[("m", "inputGain")]) - 0.75) ** 2 + 1e-6 * float(x[("m", "ac20Cut")])

    x, best, n = N.search_v2(dims, x0, f, {"leftMicType": ["1", "2"]}, lambda v: f"{v:.6g}", limit=12)
    assert x[("m", "inputGain")] == "0.75" and n == len(calls) <= 12
    assert x[("m", "ac20Cut")] == "0.5"                      # a gain under the floor does not stay


def test_search_v2_survives_a_silent_render():
    x0 = {("m", "inputGain"): "0.5"}
    vals = iter([2.0, float("inf"), 1.5, 1.4, 1.3, 1.2])
    x, best, n = N.search_v2([D("inputGain")], x0, lambda x: next(vals), {}, lambda v: f"{v:.6g}", limit=3)
    assert best == 1.5 and n == 3


def test_search_v2_skips_switches_in_the_fine_sweep():
    dims = [D("sw50rBright", kind="switch", values=("false", "true")), D("inputGain")]
    x0 = {("m", "sw50rBright"): "false", ("m", "inputGain"): "0.5"}
    seen = []

    def f(x):
        seen.append(x[("m", "sw50rBright")])
        return 1.0

    N.search_v2(dims, x0, f, {}, lambda v: f"{v:.6g}")
    assert seen.count("true") == 1


def test_boot_mean_weights_clusters_equally():
    got = N.boot_mean([("a", 1.0), ("a", 1.0), ("a", 1.0), ("b", 0.0)], n=200)
    assert got["mean"] == 0.5 and got["clusters"] == 2


def test_searched_heads_cover_only_the_space_and_stay_inside_the_heads():
    from learn import full_space as F
    from learn import knob_ceiling as K
    from learn import pipeline_fix as P

    ms = menu_s()
    for amp in P.AMPS3:
        S = ms[amp]["clean"][1]
        c, s, k = P.searched_heads(amp, S)
        keys = {(d.module, d.key) for d in K.space(amp, S)}
        D = F.by_name()
        got = {(D[n].module, D[n].key) for names, m in ((F.CONT, c), (F.SW, s), (F.CAT, k)) for n, v in zip(names, m) if v}
        assert got <= keys and len(got) >= 12
        assert ("reverb", "reverbActive") not in got and k.sum() == 2


def test_mask_leaves_plugin_rows_alone_and_drops_the_amp_label_on_real_rows():
    np = pytest.importorskip("numpy")

    from learn import full_space as F
    from learn import pipeline_fix as P

    ms = menu_s()
    n = 2
    Y = [np.ones((n, len(F.CONT))), np.ones((n, len(F.CONT))), np.ones((n, len(F.SW))), np.ones((n, len(F.SW))),
         np.ones((n, len(F.CAT))), np.ones((n, len(F.CAT))), np.array([1, 1])]
    rows = [{"i": 0, "amp": "pr12", "cls": "clean"}, {"i": 1, "amp": "pr12", "cls": "clean", "real": "u"}]
    P.mask_searched(Y, rows, ms)
    assert Y[1][0].sum() == len(F.CONT) and Y[6][0] == 1
    c, s, k = P.searched_heads("pr12", ms["pr12"]["clean"][1])
    assert (Y[1][1] == c).all() and (Y[3][1] == s).all() and (Y[5][1] == k).all() and Y[6][1] == -100


def test_the_hold_takes_only_searched_controls_from_the_answer():
    from learn import knob_ceiling as K
    from learn import pipeline_fix as P

    S = menu_s()["ac20"]["crunch"][1]
    x = dict(S)
    x[("reverb", "reverbActive")] = "true"
    x[("parameters", "inputGain")] = "-3"
    y = P.hold_outside_space(x, S, "ac20")
    assert y[("parameters", "inputGain")] == "-3"
    assert y.get(("reverb", "reverbActive")) == S.get(("reverb", "reverbActive"))
    assert {(d.module, d.key) for d in K.space("ac20", S)} <= set(y) | set(S)


def test_masked_runs_have_their_own_names():
    from learn import pipeline_fix as P

    assert P.ft_name(2) == "P2b-ft-k2"
    assert P.ft_name(2, base=P.FTM_BASE) == "P2b-ftm-k2"
    assert P.ft_name(2, True, cap=300, base=P.FTM_BASE) == "P2b-ftm-k2-inner-cap300"


def test_the_amp_loss_skips_rows_without_an_amp_label():
    torch = pytest.importorskip("torch")

    from learn import full_space as F

    z = torch.zeros
    n, nc, ns, nk = 4, len(F.CONT), len(F.SW), len(F.CAT)
    out = (torch.log_softmax(z(n, 3), -1), z(n, 3, nc) + 0.5, z(n, 3, nc), z(n, ns), [z(n, len(F.MICS)) for _ in range(nk)], z(n, 3))
    y = (z(n, nc), z(n, nc), z(n, ns), z(n, ns), z(n, nk, dtype=torch.long), z(n, nk))
    every = F.loss_fn(out, *y, torch.tensor([0, 1, 2, 0]))
    none = F.loss_fn(out, *y, torch.tensor([-100, -100, -100, -100]))
    assert torch.isfinite(none) and float(every - none) > 1.0        # ln 3 of amp loss goes


def real_rows():
    """Cycled copies: 40 records, each row twice."""
    out = []
    for j in range(40):
        for c in (0, 1):
            out.append({"i": 2 * j + c, "real": f"u{j:02d}", "amp": "ab"[j % 2], "cls": ("clean", "crunch")[j // 2 % 2], "label": j})
    return out


def test_the_curve_keeps_whole_records_nested_and_seeded():
    from learn import pipeline_fix as P

    rows = real_rows()
    q = P.curve_rows(rows, frac=0.25)
    h = P.curve_rows(rows, frac=0.5)
    units = lambda v: {r["real"] for r in v}
    assert q == P.curve_rows(rows, frac=0.25) and len(units(q)) == 8 and len(units(h)) == 20
    assert units(q) <= units(h)
    assert all(sum(r["real"] == u for r in q) == 2 for u in units(q))     # a record's copies stay together


def test_the_shuffle_gives_each_record_one_label_inside_its_cell():
    from learn import pipeline_fix as P

    rows = real_rows()
    got = P.curve_rows(rows, shuffle=True)
    assert [r["i"] for r in got] == [r["i"] for r in rows]
    per = {}
    for r in got:
        per.setdefault(r["real"], set()).add(r["label"])
    assert all(len(v) == 1 for v in per.values()) and any(r["label"] != int(r["real"][1:]) for r in got)
    assert all((r["label"] % 2, r["label"] // 2 % 2) == (int(r["real"][1:]) % 2, int(r["real"][1:]) // 2 % 2) for r in got)
